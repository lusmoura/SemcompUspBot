import os
import pytz
import sqlite3
import logging
import env_file
import dateutil.parser

import pandas as pd

from sqlite3 import Error
from datetime import datetime, timedelta, date

from telegram.ext import *
from telegram import ParseMode
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

class TelegramBot:
    schedule_filename = 'programacao_semcomp.xlsx'
    events_list = ['Todos', 
                   'Palestra', 
                   'Minicurso', 
                   'Roda de Conversa', 
                   'Feira de Oportunidades', 
                   'Concurso']

    def __init__(self):
        creds = env_file.get('.env')
        self.TOKEN = creds['TOKEN']
        self.schedule = self.get_schedule()
        
    def get_schedule(self):
        schedule = pd.read_excel(self.schedule_filename)
        schedule['Data1'] = pd.to_datetime(schedule['Data'], format='%d/%m').apply(lambda x: x.replace(year=2021))
        schedule['Hora1'] = pd.to_datetime(schedule['Hora']).apply(lambda x: x.time())
        schedule['Datetime'] = schedule.apply(lambda r : pd.datetime.combine(r['Data1'],r['Hora1']),1)
        return schedule

    def help(self, update, context):
        commands = '''Aqui o que eu posso fazer: 
        /start - Iniciar.
        /hoje - Ver eventos de hoje.
        /amanha - Ver eventos de amanhã.
        /proximos - Ver todos os eventos.
        '''
        
        context.bot.send_message(chat_id=update.message.chat_id, text=commands)

    def start(self, update, context):
        text = "Oie, bem-vindo à Semcomp! Por aqui você consegue acompanhar toda a nossa programação para não perder nenhum evento =D.\nPara começar, digite /help."
        context.bot.send_message(chat_id=update.message.chat_id, text=text)

    def get_events_buttons(self):
        buttons = []
        events_list = self.events_list

        for i in range(0, len(events_list), 2):
            buttons.append([InlineKeyboardButton(text=events_list[i], callback_data=f'{events_list[i]}'),
                            InlineKeyboardButton(text=events_list[i+1], callback_data=f'{events_list[i+1]}'),
            ])

        if len(buttons) == 0:
            return None

        markup = InlineKeyboardMarkup(buttons)
        return markup

    def get_events_text(self, date=None, type=None):
        text = ''
        schedule = self.schedule

        if date is not None:
            events = schedule[schedule['Data'] == date]

            for i, ev in events.iterrows():
                text += f"- {ev['Tipo']} | {ev['Nome']} | {ev['Data']} {ev['Hora']}\n"
        
            if text == '':
                text = 'Nada nesse dia =('
        
        elif type is not None:
            if type == 'Todos':
                events = schedule[schedule['Datetime'] >= datetime.now()]
            else:
                events = schedule[(schedule['Tipo'] == type) & (schedule['Datetime'] >= datetime.now())]
            
            for i, ev in events.iterrows():
                text += f"- {ev['Tipo']} | {ev['Nome']} | {ev['Data']} {ev['Hora']}\n"
        
            if text == '':
                text = 'Esse tipo de evento já acabou =('

        return text

    def today(self, update, context):
        chat_id = update.message.chat_id
        today = date.today().strftime('%d/%m')
        text = self.get_events_text(date=today)
        context.bot.send_message(chat_id=chat_id, text=text)        

    def tomorrow(self, update, context):
        chat_id = update.message.chat_id
        tomorrow = (date.today() + timedelta(days=1)).strftime('%d/%m')
        text = self.get_events_text(date=tomorrow)
        context.bot.send_message(chat_id=chat_id, text=text)

    def next(self, update, context):
        chat_id = update.message.chat_id
        buttons = self.get_events_buttons()
        
        context.bot.send_message(chat_id=chat_id,
                                text='Qual tipo de evento você quer ver?',
                                reply_markup=buttons,
                                parse_mode='HTML'
                                )

    def query_handler(self, update, context):
        query = update.callback_query
        query.answer()
        
        event = query.data

        self.send_event_info(update, context, event)

    def send_event_info(self, update, context, event):
        chat_id = update.effective_chat.id
        text = self.get_events_text(type=event)
        context.bot.send_message(chat_id=chat_id, text=text)

    def unknown(self, update, context):
        chat_id = update.message.chat_id
        text = "Opa, não entendi. Digite /help para ver todos os comandos."
        context.bot.send_message(chat_id=chat_id, text=text)

    def run(self):
        print("BOT ONLINE!")
        updater = Updater(token=self.TOKEN, use_context=True)
        dispatcher = updater.dispatcher
        logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

        start_handler = CommandHandler('start', self.start)
        dispatcher.add_handler(start_handler)

        today_handler = CommandHandler('hoje', self.today)
        dispatcher.add_handler(today_handler)

        tomorrow_handler = CommandHandler('amanha', self.tomorrow)
        dispatcher.add_handler(tomorrow_handler)

        next_handler = CommandHandler('proximos', self.next)
        dispatcher.add_handler(next_handler)


        help_handler = CommandHandler('help', self.help)
        dispatcher.add_handler(help_handler)

        callback_handler = CallbackQueryHandler(self.query_handler)
        dispatcher.add_handler(callback_handler)

        unknown_handler = MessageHandler(Filters.command, self.unknown)
        dispatcher.add_handler(unknown_handler)

        updater.start_polling()
        updater.idle()

if __name__ == '__main__':
    bot = TelegramBot()
    bot.run()