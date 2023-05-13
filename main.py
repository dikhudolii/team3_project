from auth_file import token  # import token
import telebot


def telegram_bot(token_value):
    bot = telebot.TeleBot(token_value)  # create bot

    @bot.message_handler(commands=['claims'])  # handler for command for getting list of claims
    def get_list_of_claims(message):
        bot.send_message(message.chat.id, "Here you can see all your claims")

    bot.infinity_polling()  # start endless loop of receiving new messages from Telegram


if __name__ == '__main__':
    telegram_bot(token)
