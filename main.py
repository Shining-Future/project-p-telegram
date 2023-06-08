from asyncio import Lock
from os import getenv, makedirs, path as osp

from projectp.inference import InferenceONNX
from projectp.processing import get_percentile
from projectp.utils import LogStub

from telegram import __version__ as TG_VER, Bot

try:
    from telegram import __version_info__
except ImportError:
    __version_info__ = (0, 0, 0, 0, 0)  # type: ignore[assignment]

if __version_info__ < (20, 0, 0, "alpha", 5):
    raise RuntimeError(
        f"This example is not compatible with your current PTB version {TG_VER}. To view the "
        f"{TG_VER} version of this example, "
        f"visit https://docs.python-telegram-bot.org/en/v{TG_VER}/examples.html"
    )
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)


TEXT, MEDIA, OTHER = range(3)

PREFIX_SOURCE = 'input'
PREFIX_TARGET = 'output'
SUFFIX_TARGET = 'output'
PATH_MODEL = 'models/yolov5s-no-nms-2022-07-07-best.onnx'

makedirs(PREFIX_SOURCE, exist_ok=True)
makedirs(PREFIX_TARGET, exist_ok=True)

lock = Lock()
log = LogStub()
inference_onnx = InferenceONNX(PATH_MODEL, log=log)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Starts the conversation and asks the user for media to inference"""
    # reply_keyboard = [["/stop"]]

    await update.message.reply_text(
        "Welcome! This is Project P Bot. Send photo(s) or video(s) within the "
        "conversation in order to detect pelicans. Send /stop to stop "
        "processing (WIP).\n\n"
        "[Attached media up to 20 MiB is supported]"
        "[Do not send photos and videos in one message]",
        # reply_markup=ReplyKeyboardMarkup(
        #     reply_keyboard, one_time_keyboard=True,
        #     input_field_placeholder="Photo or video"
        # ),
    )

    return MEDIA


async def photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the photo(s) and starts inference"""
    user_object = update.message.from_user
    user_name = user_object.username
    chat_id = update.message.chat_id
    message_id = update.message.id

    # for i, photo_ in enumerate(update.message.photo):
    i = len(update.message.photo)
    photo_ = update.message.photo[-1]
    file_photo = await photo_.get_file()
    filename_source = osp.join(
        PREFIX_SOURCE,
        f"{chat_id:012d}.{message_id:06d}.{i:03d}.{user_name}.jpg"
    )
    path_target = osp.join(PREFIX_TARGET, osp.basename(
        f"{osp.splitext(filename_source)[0]}.{SUFFIX_TARGET}.jpg"
    ))
    await file_photo.download_to_drive(filename_source)
    log.info(f"Photo of {user_object.username}: {filename_source}")
    async with lock:
        boxes_image, _, times_image = inference_onnx.process_image(
            filename_source,
            prefix_target=PREFIX_TARGET,
            suffix_target=SUFFIX_TARGET,
            feedback=None  # TODO: interrupt
        )
    percentile = round(get_percentile(boxes_image, 95))
    stats_target = f"Detected {percentile} objects in " \
                   f"{times_image['total']:.3f} sec"
    if len(boxes_image):
        await update.message.reply_photo(path_target, caption=stats_target,
                                         reply_to_message_id=message_id)
    else:
        await update.message.reply_text(f"Nothing to show. {stats_target}",
                                        reply_to_message_id=message_id)
        log.warning(f"Nothing for '{path_target}'")

    return MEDIA


async def video(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the video(s) and starts inference"""
    log.debug(f"Beginning of video callback <--")
    user_object = update.message.from_user
    user_name = user_object.username
    chat_id = update.message.chat_id
    message_id = update.message.id
    log.debug(f"Message {message_id} from {chat_id} with video by {user_name}")

    # for i, video_ in enumerate(update.message.video):
    # i = len(update.message.video)
    video_ = update.message.video  # [-1]
    file_video = await video_.get_file()
    filename_source = osp.join(
        PREFIX_SOURCE,
        f"{chat_id:012d}.{message_id:06d}.{video_.file_id}.{user_name}.mp4"
    )
    path_target = osp.join(PREFIX_TARGET, osp.basename(
        f"{osp.splitext(filename_source)[0]}.{SUFFIX_TARGET}.mp4"
    ))
    log.debug(f"Start downloading {video_.file_name} --> {filename_source}...")
    await file_video.download_to_drive(filename_source)
    log.info(f"Video of {user_object.username}: {filename_source}")
    async with lock:
        boxes_video, _, times_video = inference_onnx.process_video(
            filename_source,
            prefix_target=PREFIX_TARGET,
            suffix_target=SUFFIX_TARGET,
            progress=False,
            feedback=None  # TODO: interrupt
        )
    percentile = round(get_percentile(boxes_video, 95))
    stats_target = f"Detected {percentile} objects in " \
                   f"{times_video['total'] / 60:.3f} min"
    if len(boxes_video):
        await update.message.reply_video(path_target, caption=stats_target,
                                         reply_to_message_id=message_id)
    else:
        await update.message.reply_text(f"Nothing to show. {stats_target}",
                                        reply_to_message_id=message_id)
        log.warning(f"Nothing for '{path_target}'")

    return MEDIA


async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels and ends the conversation."""
    user_object = update.message.from_user
    log.info(f"User {user_object.first_name} canceled the conversation.")
    await update.message.reply_text(
        "Stop! Send /start to begin conversation again.",
        reply_markup=ReplyKeyboardRemove()
    )

    return ConversationHandler.END


async def error(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    ...


def main():
    """Run the bot"""
    TOKEN = getenv('TGTOKEN', None)
    assert TOKEN is not None, f"set up Telegram token (TGTOKEN) in environment!"
    # Create the Application and pass it own bot's token
    application = Application.builder().token(TOKEN).build()

    # Add conversation handler with the only state MEDIA
    handler_conversation = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            MEDIA: [MessageHandler(filters.PHOTO, photo),
                    MessageHandler(filters.VIDEO, video)],
        },
        fallbacks=[CommandHandler("stop", stop)],
    )
    # handler_photo = MessageHandler(filters.PHOTO, photo)
    # handler_video = MessageHandler(filters.VIDEO, video)

    application.add_handler(handler_conversation)
    application.add_error_handler(error)  # TODO: implement if try..except fails

    # Run the bot until the user presses Ctrl-C
    application.run_polling()


if __name__ == '__main__':
    main()
