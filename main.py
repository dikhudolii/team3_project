from telebot import types

import spreadsheet_processor
from auth_file import token  # import token
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove, InputMediaPhoto
from Domain.claim import get_claims, to_process_claim, cancel_claim, ClaimStatuses, reject_claim, Claim, ClaimTypes, \
    save_claim, get_claims_photo
from Domain.user import User

from constants import SECURITY_ROLE, SECURITY_NUMBER, SECURITY_NAME, MENU_FULL_LIST_OF_CLAIMS, MENU_TODAY_CLAIMS, \
    MENU_STATUS_CLAIMS, MENU_SECURITY_CONTACTS, MENU_APPROVE, MENU_REJECT, MENU_CHAT, MENU_CANCEL, MENU_PHOTO, \
    MENU_LOCATION, MENU_NEW_CLAIM, TYPE_TAXI, TYPE_PARKING, TYPE_GUESTS, TYPE_DELIVERY, TYPE_OTHER, \
    CANCEL_TITLE
from google_drive_photo import upload_photo_pdf

user = User()
new_claim_dict = {}


def initial_user_interface(role):
    if role == 'admin':
        message = f'Вітаємо, {user.tg_name}. Ви є адміном.\n' \
                  f"\n" \
                  f"Для ознайомлення з функціоналом боту натисніть /help. \n" \
                  f"\n" \
                  f"Оберіть одну з доступних опцій: "
        keyboard = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
        button_add_blacklisted = types.KeyboardButton(text="Додати номер у blacklist")
        button_add_admin = types.KeyboardButton(text="Додати нового адміна/охоронця")
        keyboard.add(button_add_admin)
        keyboard.add(button_add_blacklisted)
        return message, keyboard
    if role == 'guard':
        message = f'Вітаємо, {user.tg_name}. Ви є охоронцем.\n' \
                  f"\n" \
                  f"Для ознайомлення з функціоналом боту натисніть /help. \n" \
                  f"\n" \
                  f"Оберіть одну з доступних опцій: "
        keyboard = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
        button_list_of_claims = types.KeyboardButton(text="Повний перелік заявок")
        button_list_of_today_claims = types.KeyboardButton(text="Заявки за сьогодні")
        keyboard.add(button_list_of_claims, button_list_of_today_claims)
        return message, keyboard
    if role == 'tenant':
        apartment_number = spreadsheet_processor.get_apart_num(user.number, user)
        message = f"Вітаємо, {user.tg_name}. Ви є мешканцем квартири {apartment_number}. \n" \
                  f"\n" \
                  f"Для ознайомлення з функціоналом боту натисніть /help. \n" \
                  f"\n" \
                  f"Оберіть одну з доступних опцій: "
        keyboard = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
        button_new = types.KeyboardButton(text=MENU_NEW_CLAIM)
        button_list_of_claims = types.KeyboardButton(text=MENU_STATUS_CLAIMS)
        button_contacts = types.KeyboardButton(text=MENU_SECURITY_CONTACTS)
        keyboard.add(button_new, button_list_of_claims, button_contacts)
        return message, keyboard

    return 'Ви не маєте доступу до чат бота', None


def telegram_bot(token_value):
    bot = telebot.TeleBot(token_value)  # create bot

    global process_comment_step, process_description_step, process_add_photo_claim_step, process_save_claim_step, \
        process_parking_step, process_number_step, process_guests_step, process_kpp_step

    def simple_reply_markup(row_width: int, text_arr: list):
        markup = types.ReplyKeyboardMarkup(row_width=row_width, resize_keyboard=True)
        for element in text_arr:
            button = types.KeyboardButton(text=element)
            markup.add(button)
        return markup

    def generate_menu_checkpoint():
        markup = simple_reply_markup(3, spreadsheet_processor.get_kpp_options_from_spreadsheet())
        return markup

    # Code from Angela's github
    @bot.message_handler(commands=['new'])
    @bot.message_handler(func=lambda message: message.text == MENU_NEW_CLAIM)
    def handle_new_request(message):
        keyboard = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
        button1 = types.KeyboardButton(text=TYPE_TAXI)
        button2 = types.KeyboardButton(text=TYPE_PARKING)
        button3 = types.KeyboardButton(text=TYPE_GUESTS)
        button4 = types.KeyboardButton(text=TYPE_DELIVERY)
        button5 = types.KeyboardButton(text=TYPE_OTHER)
        button6 = types.KeyboardButton(text=CANCEL_TITLE)
        keyboard.add(button1, button2, button3, button4, button5, button6)
        bot.send_message(message.chat.id, "Оберіть тип заявки:", reply_markup=keyboard)

    @bot.message_handler(func=lambda message: message.text == CANCEL_TITLE)
    def cancel_creating_claim(message):
        result = initial_user_interface("tenant")
        bot.send_message(message.chat.id, "Оберіть одну з доступних опцій:", reply_markup=result[1])

    # Code from Angela's github
    @bot.message_handler(
        func=lambda message: message.text in [TYPE_TAXI, TYPE_PARKING, TYPE_GUESTS, TYPE_DELIVERY,
                                              TYPE_OTHER])
    def handle_request_type(message):
        request_type = message.text

        chat_id = message.chat.id
        phone = spreadsheet_processor.get_phone_num_by_user_id(chat_id)

        apartment_number = spreadsheet_processor.get_apart_num(phone, user)
        new_claim = Claim.create_new(phone, apartment_number)
        chat_id = message.chat.id

        match request_type:
            case "Пропуск таксі":
                new_claim.type = ClaimTypes.Taxi.value
                new_claim_dict[chat_id] = new_claim

                msg = bot.send_message(message.chat.id, "Введіть номер автомобіля таксі:")
                bot.register_next_step_handler(msg, process_number_step)

            case "Пропуск кур'єра":
                new_claim.type = ClaimTypes.Delivery.value
                new_claim_dict[chat_id] = new_claim

                markup = simple_reply_markup(1, ["Невідомий номер"])
                msg = bot.send_message(message.chat.id,
                                       "Введіть номер автомобіля кур'єра:",
                                       reply_markup=markup)
                bot.register_next_step_handler(msg, process_number_step)

            case "Пропуск гостей":
                new_claim.type = ClaimTypes.Guests.value
                new_claim_dict[chat_id] = new_claim

                markup = simple_reply_markup(1, ["Гості без авто"])
                msg = bot.send_message(message.chat.id,
                                       "Введіть номер автомобіля або оберіть варіант 'гості без авто':",
                                       reply_markup=markup)
                bot.register_next_step_handler(msg, process_number_step)

            case "Проблема парковки":
                new_claim.type = ClaimTypes.ProblemWithParking.value
                new_claim_dict[chat_id] = new_claim

                markup = simple_reply_markup(2, ["Моє авто заблоковано", "Автомобіль стоїть у недозволеному місці"])
                msg = bot.send_message(message.chat.id,
                                       "Уточніть характер проблеми:",
                                       reply_markup=markup)
                bot.register_next_step_handler(msg, process_parking_step)

            case "Заявка на інше":
                new_claim.type = ClaimTypes.Other.value
                new_claim_dict[chat_id] = new_claim

                msg = bot.send_message(message.chat.id,
                                       "Напишіть текст заявки:",
                                       reply_markup=ReplyKeyboardRemove())
                bot.register_next_step_handler(msg, process_description_step)

    def process_number_step(message):
        try:
            chat_id = message.chat.id
            claim = new_claim_dict[chat_id]
            answer = message.text

            match claim.type:
                case ClaimTypes.Taxi.value:
                    if len(answer) < 5:
                        msg = bot.reply_to(message, 'Ви повинні ввести номер автомобіля')
                        bot.register_next_step_handler(msg, process_number_step)
                        return

                    claim.vehicle_number = answer

                case ClaimTypes.Delivery.value:
                    if answer == "Невідомий номер":
                        claim.vehicle_number = ""
                        claim.description = answer
                    else:
                        if len(answer) < 5:
                            markup_unknown = simple_reply_markup(1, ["Невідомий номер"])

                            msg = bot.send_message(chat_id, 'Ви повинні ввести номер '
                                                            'автомобіля або обрати опцію "Невідомий номер"',
                                                   reply_markup=markup_unknown)
                            bot.register_next_step_handler(msg, process_number_step)
                            return

                        claim.vehicle_number = answer

                case ClaimTypes.Guests.value:
                    if answer == "Гості без авто":
                        msg = bot.send_message(chat_id, 'Введіть ПІБ гостей в одному повідомленні',
                                               reply_markup=ReplyKeyboardRemove())
                        bot.register_next_step_handler(msg, process_guests_step)
                        return
                    else:
                        if len(answer) < 5:
                            markup_without_auto = simple_reply_markup(1, ["Гості без авто"])

                            msg = bot.send_message(chat_id, 'Ви повинні ввести номер '
                                                            'автомобіля або обрати опцію "Гості без авто"',
                                                   reply_markup=markup_without_auto)
                            bot.register_next_step_handler(msg, process_number_step)
                            return
                        claim.vehicle_number = answer

                case ClaimTypes.ProblemWithParking.value:
                    if len(answer) < 5:
                        msg = bot.reply_to(message, 'Введіть номер автомобіля порушника')
                        bot.register_next_step_handler(msg, process_number_step)
                        return
                    claim.vehicle_number = answer

            markup_without_comment = simple_reply_markup(1, ["Без коментарів"])
            msg = bot.send_message(chat_id,
                                   "Можете додати коментар до вашої заявки",
                                   reply_markup=markup_without_comment)

            bot.register_next_step_handler(msg, process_comment_step)

        except Exception as e:
            bot.reply_to(message, 'Сервіс тимчасово недоступний')

    def process_guests_step(message):
        try:
            chat_id = message.chat.id
            guests = message.text
            claim = new_claim_dict[chat_id]

            if len(guests) == 0:
                msg = bot.send_message(chat_id, 'Введіть ПІБ гостей в одному повідомленні',
                                       reply_markup=ReplyKeyboardRemove())
                bot.register_next_step_handler(msg, process_guests_step)
                return

            claim.visitors_data = guests

            markup_without_comment = simple_reply_markup(1, ["Без коментарів"])
            msg = bot.send_message(chat_id,
                                   "Можете додати коментар до вашої заявки", reply_markup=markup_without_comment)
            bot.register_next_step_handler(msg, process_comment_step)
        except Exception as e:
            bot.reply_to(message, 'Сервіс тимчасово недоступний')

    def process_comment_step(message):
        try:
            chat_id = message.chat.id
            comment = message.text
            claim = new_claim_dict[chat_id]

            if comment != "Без коментарів":
                claim.description = comment

            if claim.type == ClaimTypes.Other.value or claim.type == ClaimTypes.ProblemWithParking.value:
                markup = simple_reply_markup(1, ["Без фото"])

                msg = bot.send_message(chat_id,
                                       f"Додайте фото до вашої заявки",
                                       reply_markup=markup)

                bot.register_next_step_handler(msg, process_add_photo_claim_step)
            else:
                markup = generate_menu_checkpoint()
                msg = bot.send_message(chat_id,
                                       'Оберіть КПП',
                                       reply_markup=markup)
                bot.register_next_step_handler(msg, process_kpp_step)

        except Exception as e:
            bot.reply_to(message, 'Сервіс тимчасово недоступний')

    def process_description_step(message):
        try:
            chat_id = message.chat.id
            description = message.text
            claim = new_claim_dict[chat_id]

            if len(description) == 0:
                msg = bot.send_message(chat_id, 'Напишіть текст заявки',
                                       reply_markup=ReplyKeyboardRemove())
                bot.register_next_step_handler(msg, process_description_step)
                return

            claim.description = description

            markup = simple_reply_markup(1, ["Без фото"])
            msg = bot.send_message(chat_id,
                                   f"Додайте фото до вашої заявки",
                                   reply_markup=markup)

            bot.register_next_step_handler(msg, process_add_photo_claim_step)
        except Exception as e:
            bot.reply_to(message, 'Сервіс тимчасово недоступний')

    def process_kpp_step(message):
        try:
            chat_id = message.chat.id
            kpp = message.text
            claim = new_claim_dict[chat_id]
            claim.checkpoint = kpp

            markup = simple_reply_markup(2, ["Так", "Ні"])

            msg = bot.send_message(chat_id,
                                   f"{claim}. Бажаєте зберегти заявку?",
                                   reply_markup=markup)
            bot.register_next_step_handler(msg, process_save_claim_step)
        except Exception as e:
            bot.reply_to(message, 'Сервіс тимчасово недоступний')

    def process_parking_step(message):
        try:
            chat_id = message.chat.id
            claim = new_claim_dict[chat_id]
            claim.description = message.text

            msg = bot.send_message(chat_id, 'Введіть номер авто порушника', reply_markup=ReplyKeyboardRemove())
            bot.register_next_step_handler(msg, process_number_step)

        except Exception as e:
            bot.reply_to(message, 'Сервіс тимчасово недоступний')

    def process_add_photo_claim_step(message):
        try:
            chat_id = message.chat.id
            claim = new_claim_dict[chat_id]
            if message.content_type == 'photo':
                file_id = message.photo[-1].file_id
                if claim.photos is not None and len(claim.photos) > 0:
                    claim.photos.append(file_id)
                else:
                    claim.photos = [file_id]
            if message.content_type == 'location':
                location = message.location
                claim.geolocation = f"{location.latitude};{location.longitude}"

            text = message.text
            if message.content_type == 'photo' or (text is not None and text == "Без фото"):
                markup = simple_reply_markup(1, ["Без геолокації"])
                msg = bot.send_message(chat_id,
                                       f"Завантажити ще одне фото чи геолокацію до вашої заявки",
                                       reply_markup=markup)
                bot.register_next_step_handler(msg, process_add_photo_claim_step)
                return

            markup = simple_reply_markup(2, ["Так", "Ні"])

            msg = bot.send_message(chat_id,
                                   f"{claim}. Бажаєте зберегти заявку?",
                                   reply_markup=markup)
            bot.register_next_step_handler(msg, process_save_claim_step)

        except Exception as e:
            bot.reply_to(message, 'Сервіс тимчасово недоступний')

    def process_save_claim_step(message):
        try:
            answer = message.text
            result = initial_user_interface("tenant")
            if answer == 'Так':
                chat_id = message.chat.id
                claim = new_claim_dict[chat_id]
                claim_number = save_claim(claim)
                bot.send_message(message.chat.id, f"Ваша заявка успішно збережена за номером {claim_number}.",
                                 reply_markup=result[1])
                # get all security
                # get all security user_ids
                # send message with claim
                # send photo if exist
                security_user_ids = spreadsheet_processor.get_guard_user_ids()
                for user_id in security_user_ids:
                    bot.send_message(chat_id=user_id,
                                     text=f"Нова заявка:\n {claim}")
                    if claim.photos is not None and len(claim.photos) > 0:
                        if len(claim.photos) == 1:
                            bot.send_photo(chat_id=user_id,
                                           photo=claim.photos[0],
                                           caption=f"Фото до заявки {claim.number}")
                        else:
                            all_photos = []
                            for file_id in claim.photos:
                                media_photo = InputMediaPhoto(media=file_id)
                                all_photos.append(media_photo)

                            bot.send_media_group(user_id, all_photos)

                    if claim.geolocation is not None:
                        coordinates = str(claim.geolocation).split(";")
                        bot.send_location(chat_id=user_id,
                                          latitude=float(coordinates[0]),
                                          longitude=float(coordinates[1]))
            else:
                bot.send_message(message.chat.id, "Збереження заявки скасовано", reply_markup=result[1])
        except Exception as e:
            bot.reply_to(message, 'Сервіс тимчасово недоступний')

    @bot.message_handler(func=lambda message: message.text == MENU_SECURITY_CONTACTS)
    def get_security_contact(message):
        security_list = ""
        data = spreadsheet_processor.get_securities()
        for row in data:
            if row[SECURITY_ROLE] == "guard":
                security_list += f"Номер телефону: {row[SECURITY_NUMBER]}, ПІБ: {row[SECURITY_NAME]}\n"

        bot.send_message(message.chat.id, security_list)

    @bot.callback_query_handler(func=lambda call: True)
    def processing_request(call):
        command, claim_id, additional_parameter = str(call.data).split(',')
        claim_id = claim_id.strip()

        match command:
            case "approve":
                to_process_claim(claim_id, call.from_user.full_name)
                bot.send_message(call.message.chat.id,
                                 f"Заявкy № {claim_id} опрацьовано")
            case "reject":
                reject_claim(claim_id, call.from_user.full_name)
                bot.send_message(call.message.chat.id,
                                 f"Заявку № {claim_id} відхилено ")
            case "cancel":
                cancel_claim(claim_id)
                bot.send_message(call.message.chat.id,
                                 f"Ви успішно видалили заявку № {claim_id}")
            case "chat":
                user_id = spreadsheet_processor.get_user_id_by_phone_num(additional_parameter)
                try:
                    bot.send_message(chat_id=user_id, text=f"Добрий день! Вас турбує охорона ЖК")
                except Exception as e:
                    bot.send_message(call.message.chat.id, f"Заявка № {claim_id}: Неможливо почати чат з мешканцем, "
                                                           f"спробуйте сконтактувати з ним по телефону: {additional_parameter}",
                                     parse_mode="Markdown")
            case "photos":
                photo = get_claims_photo(claim_id)
                bot.reply_to(message=call.message,
                             text=f"Фото до заявки {claim_id}")
                bot.send_photo(chat_id=call.message.chat.id,
                               photo=photo)
            case "location":
                coordinates = str(additional_parameter).split(";")
                bot.reply_to(message=call.message,
                             text=f"Геолокація до заявки {claim_id}")
                bot.send_location(chat_id=call.message.chat.id,
                                  latitude=float(coordinates[0]),
                                  longitude=float(coordinates[1]))

    @bot.message_handler(
        func=lambda message: message.text in [MENU_FULL_LIST_OF_CLAIMS, MENU_TODAY_CLAIMS, MENU_STATUS_CLAIMS])
    def get_list_of_claims(message):
        chat_id = message.chat.id
        phone = spreadsheet_processor.get_phone_num_by_user_id(chat_id)
        role = spreadsheet_processor.get_user_role(phone, user)
        only_new = str(message.text) == MENU_TODAY_CLAIMS
        is_inhabitant = role == 'tenant'
        claims = get_claims(is_inhabitant,
                            phone,
                            only_new=only_new)

        if len(claims) == 0:
            bot.send_message(message.chat.id,
                             f"За поданими критеріями заявок в системі не зареєстровано")

        # processing claims
        for claim in claims:
            # if user is security he would have more options to do with claim
            if role == 'guard':
                if claim.status == ClaimStatuses.New.value:
                    markup_inline = InlineKeyboardMarkup(row_width=2)
                    item_approve = InlineKeyboardButton(
                        text=MENU_APPROVE,
                        callback_data=f"approve,{claim.number},")
                    item_reject = InlineKeyboardButton(
                        text=MENU_REJECT,
                        callback_data=f"reject,{claim.number},")
                    item_chat = InlineKeyboardButton(
                        text=MENU_CHAT,
                        callback_data=f"chat,{claim.number},{claim.phone_number}")

                    markup_inline.add(item_approve, item_reject, item_chat)

                    if claim.photos is not None and len(claim.photos) > 0:
                        item_photos = InlineKeyboardButton(
                            text=MENU_PHOTO,
                            callback_data=f"photos,{claim.number},")
                        markup_inline.add(item_photos)

                    if claim.geolocation is not None and len(claim.geolocation) > 0:
                        item_location = InlineKeyboardButton(
                            text=MENU_LOCATION,
                            callback_data=f"location,{claim.number},{claim.geolocation}")
                        markup_inline.add(item_location)

                    bot.send_message(message.chat.id,
                                     f"{claim}",
                                     reply_markup=markup_inline)
                else:
                    bot.send_message(message.chat.id,
                                     f"{claim}")

            # if user is inhabitant he could only cancel claim in case it in status New
            elif role == 'tenant':
                if claim.status == ClaimStatuses.New.value:

                    markup_inline = InlineKeyboardMarkup()
                    item_cancel = InlineKeyboardButton(
                        text=MENU_CANCEL,
                        callback_data=f"cancel,{claim.number},")
                    markup_inline.add(item_cancel)

                    bot.send_message(message.chat.id,
                                     f"{claim}",
                                     reply_markup=markup_inline)
                else:
                    bot.send_message(message.chat.id,
                                     f"{claim.status}: {claim.processed_date} {claim}")

    @bot.message_handler(commands=['start'])
    def start(message):
        user.tg_name = message.from_user.full_name
        if message.contact is None or message.contact.phone_number is None:
            keyboard = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
            button = types.KeyboardButton(text="Відправити свій контакт", request_contact=True)
            keyboard.add(button)

            bot.send_message(message.chat.id,
                             "Натисніть кнопку 'Відправити контакт' для передачі свого особистого контакту.",
                             reply_markup=keyboard)
        else:
            contact = message.contact
            phone_number = str(contact.phone_number)
            role = spreadsheet_processor.get_user_role(phone_number, user)

            if role is not None:
                spreadsheet_processor.add_user_id(contact.phone_number, contact.user_id)

            if role == 'tenant':
                apartment_number = spreadsheet_processor.get_apart_num(phone_number, user)
                debt = spreadsheet_processor.check_debt(apartment_number)

                if debt > 240:
                    bot.send_message(message.chat.id,
                                     f'У вас заборгованість {debt} гривень, зверніться до адміністратора або завантажте квитанцію про оплату.')
                    return

            answer = initial_user_interface(role)
            bot.send_message(message.chat.id, answer[0], reply_markup=answer[1])

    @bot.message_handler(content_types=['contact'])
    def handle_contact(message):
        user.tg_name = message.from_user.full_name

        contact = message.contact
        phone_number = str(contact.phone_number)

        # phone_number = str("380951993971")
        # phone_number = "380849784670"
        # phone_number = "380799761264" # - тест борг
        # phone_number = "380849784670"  # - тест мешканця
        # phone_number = "87654321"     # - тест охоронця

        role = spreadsheet_processor.get_user_role(phone_number, user)

        if role is not None:
            spreadsheet_processor.add_user_id(contact.phone_number, contact.user_id)

        if role == 'tenant':
            apartment_number = spreadsheet_processor.get_apart_num(phone_number, user)
            debt = spreadsheet_processor.check_debt(apartment_number)

            if debt > 240:
                bot.send_message(message.chat.id,
                                 f'У вас заборгованість {debt} гривень, зверніться до адміністратора або завантажте квитанцію про оплату.')
                return

        answer = initial_user_interface(role)
        bot.send_message(message.chat.id, answer[0], reply_markup=answer[1])

    @bot.message_handler(content_types=['photo', 'document'])
    def handle_payment_receipt(message):
        if message.content_type == 'document':
            if message.document.mime_type == 'application/pdf':
                file_info = bot.get_file(message.document.file_id)
            else:
                bot.reply_to(message, "Вибачте, приймаються лише pdf або фото.")
                return
        else:
            file_info = bot.get_file(message.photo[-1].file_id)

        phone_number = spreadsheet_processor.get_phone_num_by_user_id(message.from_user.id)
        apartment_number = spreadsheet_processor.get_apart_num(phone_number, user)

        admin_numbers = spreadsheet_processor.get_admin_data_from_spreadsheet()
        for number in admin_numbers:
            admin_id = spreadsheet_processor.get_user_id_by_phone_num(number)

            if admin_id is None:
                continue

            text = f"Надіслана квитанція про оплату боргу від квартири {apartment_number}."
            bot.send_message(admin_id, text)

        upload_photo_pdf(file_info, apartment_number)

        bot.reply_to(message, "Дякуємо! Ваша квитанція на розгляді в адміністратора.")

    @bot.message_handler(content_types=['location'])
    def handle_location(message):
        user_id = message.from_user.id
        location = message.location
        print(f"User ID: {user_id}, Latitude: {location.latitude}, Longitude: {location.longitude}")

    @bot.message_handler(commands=['help'])
    def help_(message):
        user_id = message.from_user.id
        user = message.from_user
        phone_number = spreadsheet_processor.get_phone_num_by_user_id(user_id)
        user_role = spreadsheet_processor.get_user_role(phone_number, user)

        if user_role == 'admin':
            help_message = '''
            Ось декілька корисних команд для Вас:
            /start - початок роботи з ботом;
            /blacklist - додати користувача у blacklist;
            /admin - додати нового охоронця або адміністратора.
            '''
        elif user_role == 'guard':
            help_message = '''
            Ось декілька корисних команд для Вас:
            /start - початок роботи з ботом;
            '''
        elif user_role == 'tenant':
            help_message = '''
            Ось декілька корисних команд для Вас:
            /start - початок роботи з ботом;
            /new - створити нову заявку;
            '''
        else:
            help_message = "Вибачте, але ми не можемо визначити вашу роль. Зверніться до адміністратора або перезавантажте бот за допомогою команди /start"

        bot.send_message(message.chat.id, help_message)

    @bot.message_handler(func=lambda message: message.text == 'Додати номер у blacklist')
    def handle_blacklist_add(message):
        msg = 'Будь ласка, введіть номер, який потрібно додати до blacklist у форматі: /blacklist [номер]'
        bot.send_message(message.chat.id, msg)

    @bot.message_handler(func=lambda message: message.text == 'Додати нового адміна/охоронця')
    def handle_admin_add(message):
        msg = 'Будь ласка, введіть номер та роль нового користувача у форматі: /admin [номер] [роль] [Прізвище]'
        bot.send_message(message.chat.id, msg)

    @bot.message_handler(commands=['blacklist'])
    def handle_blacklist_add_command(message):
        try:
            parts = message.text.split()
            if len(parts) != 2:
                raise ValueError
            number = parts[1]
            # Перевіряємо, чи є number коректним номером телефону.
            # Якщо все в порядку, додаємо номер до blacklist
            spreadsheet_processor.add_to_blacklist(number)
            bot.send_message(message.chat.id, "Номер успішно додано до blacklist!")
        except ValueError:
            bot.send_message(message.chat.id,
                             "Некоректний формат. Будь ласка, введіть номер у форматі: /blacklist [номер]")

    @bot.message_handler(commands=['admin'])
    def handle_admin_add_command(message):
        try:
            parts = message.text.split()
            if len(parts) != 4:
                raise ValueError
            number = parts[1]
            role = parts[2]
            surname = parts[3]
            # Перевіряємо, чи є number коректним номером телефону, і чи є role валідною роллю.
            # Якщо все в порядку, додаємо номер і роль до  листа admin_guard
            spreadsheet_processor.add_admin(number, role, surname)
            bot.send_message(message.chat.id, "Новий адмін/охоронець успішно доданий!")
        except ValueError:
            bot.send_message(message.chat.id,
                             "Некоректний формат. Будь ласка, введіть дані у форматі: \admin [номер] [роль] [Прізвище]")

    # Enable saving next step handlers to file "./.handlers-saves/step.save".
    # Delay=2 means that after any change in next step handlers (e.g. calling register_next_step_handler())
    # saving will hapen after delay 2 seconds.
    bot.enable_save_next_step_handlers(delay=2)

    # Load next_step_handlers from save file (default "./.handlers-saves/step.save")
    # WARNING It will work only if enable_save_next_step_handlers was called!
    bot.load_next_step_handlers()

    bot.infinity_polling()  # start endless loop of receiving new messages from Telegram


if __name__ == '__main__':
    telegram_bot(token)
