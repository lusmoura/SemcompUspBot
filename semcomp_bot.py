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
    overflow_houses = {
                        'Agamotto':'Após perceber diversas ameaças temporais, o Doutor Estranho confiou sua joia àqueles que mais confia: vocês! Bem vindos à casa Agamotto! Focados sempre na resolução de problemas, usamos nossas diferentes magias para alcançar a vitória, superando as fileiras de oponentes que possam aparecer pelo caminho. Então abram seus portais e venham com a gente para mais uma conquista!',
                        'DeLorean':'Great Scott!\nVocês estavam tranquilos no palquinho quando, de repente, surge um carro entre faíscas e raios e invade o local e de dentro dele sai um homem de idade, com cabelo branco bagunçado com uma vestimenta dos anos 80. Antes que pudessem fazer qualquer pergunta, vocês ouvem as seguintes palavras: "Depressa! O poder sobre o tempo caiu em mãos erradas! Utilizem esta máquina com responsabilidade e não deixem que interfiram na nossa linha do tempo! Não se esqueça, o futuro ainda não está escrito, o de ninguém está. Seu futuro será o que você quiser, então faça dele algo bom',
                        'Ocarina':'Evoé, caros Representantes do Reino Sagrado! Diante dos poderes vindos de Farore, Din e Nayru, a Triforce que rege Hyrule, um item chave foi atribuída como elo entre as eras, a chamada Ocarina do Tempo. Usando de seus poderes e da magia das músicas que permeiam todo esse mundo, desafie os oponentes que ousarem destruir esse equilíbrio. Saquem suas ocarinas e partam para uma nova canção da vitória!',
                        'Tardis':'O Doutor (Doutor quem?) detectou alguém tentando alterar um ponto fixo no tempo e resolveu viajar um milhão de anos no futuro para visitar a biblioteca do ICMC e pesquisar o que ele pode fazer sobre isso. Mas não se preocupem! Ele já os informou sobre todos os perigos e com certeza, eventualmente, vai aparecer e resolver tudo com sua chave de fenda sônica que, apesar do nome, raramente é usada para apertar ou afrouxar parafusos.Muito cuidado! Antes de ir, o Doutor (Doutor quem?) disse que esse é um inimigo pior do que os Daleks e os Cybermen, mais astuto do que o Mestre e mais perigoso do que os Vashta Nerada. Por isso, não pisquem nem por um segundo e sempre confiem uns nos outros, mas em mais ninguém! Allons-y!'
                        }

    def __init__(self):
        creds = env_file.get('.env')
        self.TOKEN = creds['TOKEN']
        self.schedule = self.get_schedule()
    
    def log(self, event, id):
        text = f'{id} - {event}'
        logging.info(text)

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
        /overflow - Ver detalhes das casas do Overflow.
        '''
        
        context.bot.send_message(chat_id=update.message.chat_id, text=commands)

    def start(self, update, context):
        chat_id = update.message.chat_id
        text = "Oie, bem-vindo à Semcomp! Por aqui você consegue acompanhar toda a nossa programação para não perder nenhum evento =D.\nPara começar, digite /help."
        context.bot.send_message(chat_id=chat_id, text=text)
        self.log('Start', chat_id)

    def get_events_buttons(self):
        buttons = []
        events_list = self.events_list  

        for i in range(0, len(events_list), 2):
            buttons.append([InlineKeyboardButton(text=events_list[i], callback_data=f'event-{events_list[i]}'),
                            InlineKeyboardButton(text=events_list[i+1], callback_data=f'event-{events_list[i+1]}'),
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
        chat_id = update.effective_chat.id
        today = date.today().strftime('%d/%m')
        text = self.get_events_text(date=today)
        context.bot.send_message(chat_id=chat_id, text=text)        
        self.log('Hoje', chat_id)

    def tomorrow(self, update, context):
        chat_id = update.effective_chat.id
        tomorrow = (date.today() + timedelta(days=1)).strftime('%d/%m')
        text = self.get_events_text(date=tomorrow)
        context.bot.send_message(chat_id=chat_id, text=text)
        self.log('Amanhã', chat_id)

    def next(self, update, context):
        chat_id = update.effective_chat.id
        buttons = self.get_events_buttons()
        
        context.bot.send_message(chat_id=chat_id,
                                text='Qual tipo de evento você quer ver?',
                                reply_markup=buttons,
                                parse_mode='HTML'
                                )
        self.log('Próximos', chat_id)

    def send_event_info(self, update, context, event):
        chat_id = update.effective_chat.id
        text = self.get_events_text(type=event)
        context.bot.send_message(chat_id=chat_id, text=text)

    def get_overflow_buttons(self):
        houses = list(self.overflow_houses.keys())

        buttons = [[InlineKeyboardButton(text=houses[0], callback_data=f'overflow-{houses[0]}'),
                        InlineKeyboardButton(text=houses[1], callback_data=f'overflow-{houses[1]}')],
                       [InlineKeyboardButton(text=houses[2], callback_data=f'overflow-{houses[2]}'),
                        InlineKeyboardButton(text=houses[3], callback_data=f'overflow-{houses[3]}')],
                       [InlineKeyboardButton(text='Todas', callback_data=f'overflow-Todas')]]
        
        markup = InlineKeyboardMarkup(buttons)
        return markup

    def overflow(self, update, context):
        chat_id = update.effective_chat.id
        buttons = self.get_overflow_buttons()
        
        context.bot.send_message(chat_id=chat_id,
                                text='Qual casa você quer ver?',
                                reply_markup=buttons,
                                parse_mode='HTML'
                                )
        self.log('Overflow', chat_id)

    def send_overflow_info(self, update, context, house):
        chat_id = update.effective_chat.id
        text = self.get_oveflow_text(house)
        context.bot.send_message(chat_id=chat_id, text=text)
    
    def get_oveflow_text(self, house):
        if house == 'Todas':
            text = 'Pontuação de todas as casas'
        else:
            text = self.overflow_houses[house] + '\n\n' + 'Pontuação: 0'
        
        return text

    def query_handler(self, update, context):
        query = update.callback_query
        query.answer()
        
        callback_type = query.data.split('-')[0]
        
        if callback_type == 'event':
            event = query.data.split('-')[1]
            self.send_event_info(update, context, event)
        elif callback_type == 'overflow':
            house = query.data.split('-')[1]
            self.send_overflow_info(update, context, house)

    def unknown(self, update, context):
        chat_id = update.effective_chat.id
        text = "Opa, não entendi. Digite /help para ver todos os comandos."
        context.bot.send_message(chat_id=chat_id, text=text)
        self.log('Desconhecido', chat_id)

    def run(self):
        updater = Updater(token=self.TOKEN, use_context=True)
        dispatcher = updater.dispatcher
        logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.INFO)

        start_handler = CommandHandler('start', self.start)
        dispatcher.add_handler(start_handler)

        today_handler = CommandHandler('hoje', self.today)
        dispatcher.add_handler(today_handler)

        tomorrow_handler = CommandHandler('amanha', self.tomorrow)
        dispatcher.add_handler(tomorrow_handler)

        next_handler = CommandHandler('proximos', self.next)
        dispatcher.add_handler(next_handler)

        overflow_handler = CommandHandler('overflow', self.overflow)
        dispatcher.add_handler(overflow_handler)

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