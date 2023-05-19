from auth_file import token  # import token
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from Domain.claim import Claim, get_claims
from Domain.user import User, get_user_by_id


def telegram_bot(token_value):
    bot = telebot.TeleBot(token_value)  # create bot

    @bot.callback_query_handler(func=lambda call: True)
    def processing_request(call):
        command, claim_id = str(call.data).split(',')
        claim_id = claim_id.strip()

        match command:
            case "approve":
                bot.send_message(call.message.chat.id,
                                 f"Set claim {claim_id} status Approved and set approving datetime")
            case "reject":
                bot.send_message(call.message.chat.id, f"Set claim {claim_id} status Rejected"
                                                       f" and set rejected datetime and reason")
            case "cancel":
                bot.send_message(call.message.chat.id,
                                 f"Set claim {claim_id} status Canceled and set canceling datetime")
            case "chat":
                bot.send_message(call.message.chat.id, f"Start chat with inhabitant")

    @bot.message_handler(commands=['claims'])  # handler for getting list of claims
    def get_list_of_claims(message):
        claims = get_claims(message.from_user.id)       # get list of claims from db ???
        user = get_user_by_id(message.from_user.id)     # get user info to deside is security or inhabitant from db???

        # processing claims
        for claim in claims:
            # if user is security he would have more options to do with claim
            if user.is_security:
                markup_inline = InlineKeyboardMarkup()
                item_approve = InlineKeyboardButton(text='Підтвердити', callback_data=f"approve, {claim.id}")
                item_chat = InlineKeyboardButton(text='Чат з мешканцем', callback_data=f"chat, {claim.id}")
                item_reject = InlineKeyboardButton(text='Відхилити', callback_data=f"reject, {claim.id}")
                markup_inline.add(item_approve, item_reject, item_chat)
                bot.send_message(message.chat.id,
                                 f"Claim from {claim.phone_number}, {claim.type}",
                                 reply_markup=markup_inline)

            # if user is inhabitant he could only cancel claim in case it in status New
            elif user.is_inhabitant:
                if claim.status == "New":
                    markup_inline = InlineKeyboardMarkup()
                    item_cancel = InlineKeyboardButton(text='Скасувати', callback_data=f"cancel, {claim.id}")
                    markup_inline.add(item_cancel)
                    bot.send_message(message.chat.id,
                                     f"Заявка {claim.type} {claim.vehicle_number} статус {claim.status}",
                                     reply_markup=markup_inline)
                else:
                    bot.send_message(message.chat.id,
                                     f"Заявка {claim.type} {claim.vehicle_number} статус {claim.status}")

    bot.infinity_polling()  # start endless loop of receiving new messages from Telegram


if __name__ == '__main__':
    telegram_bot(token)
