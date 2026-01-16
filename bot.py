import asyncio
import aiohttp
from datetime import datetime
from typing import Dict, List, Optional
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

class ArbitrageBot:
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.monitoring = {}
        
    async def init_session(self):
        if not self.session:
            self.session = aiohttp.ClientSession()
    
    async def close_session(self):
        if self.session:
            await self.session.close()
    
    # ========== BINANCE ==========
    async def get_binance_price(self, symbol: str) -> Optional[Dict]:
        try:
            url = f"https://api.binance.com/api/v3/ticker/24hr?symbol={symbol}"
            async with self.session.get(url, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return {
                        'exchange': 'Binance',
                        'symbol': symbol,
                        'price': float(data['lastPrice']),
                        'volume': float(data['volume']),
                        'bid': float(data['bidPrice']),
                        'ask': float(data['askPrice'])
                    }
        except Exception as e:
            print(f"Ошибка Binance {symbol}: {e}")
        return None
    
    # ========== GATE.IO ==========
    async def get_gateio_price(self, symbol: str) -> Optional[Dict]:
        try:
            url = f"https://api.gateio.ws/api/v4/spot/tickers?currency_pair={symbol}"
            async with self.session.get(url, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data:
                        ticker = data[0]
                        return {
                            'exchange': 'Gate.io',
                            'symbol': symbol,
                            'price': float(ticker['last']),
                            'volume': float(ticker['base_volume']),
                            'bid': float(ticker['highest_bid']),
                            'ask': float(ticker['lowest_ask'])
                        }
        except Exception as e:
            print(f"Ошибка Gate.io {symbol}: {e}")
        return None
    
    # ========== BYBIT ==========
    async def get_bybit_price(self, symbol: str) -> Optional[Dict]:
        try:
            url = f"https://api.bybit.com/v5/market/tickers?category=spot&symbol={symbol}"
            async with self.session.get(url, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data['retCode'] == 0 and data['result']['list']:
                        ticker = data['result']['list'][0]
                        return {
                            'exchange': 'Bybit',
                            'symbol': symbol,
                            'price': float(ticker['lastPrice']),
                            'volume': float(ticker['volume24h']),
                            'bid': float(ticker['bid1Price']),
                            'ask': float(ticker['ask1Price'])
                        }
        except Exception as e:
            print(f"Ошибка Bybit {symbol}: {e}")
        return None
    
    # ========== KUCOIN ==========
    async def get_kucoin_price(self, symbol: str) -> Optional[Dict]:
        try:
            url = f"https://api.kucoin.com/api/v1/market/orderbook/level1?symbol={symbol}"
            async with self.session.get(url, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data['code'] == '200000':
                        ticker = data['data']
                        return {
                            'exchange': 'KuCoin',
                            'symbol': symbol,
                            'price': float(ticker['price']),
                            'volume': 0,
                            'bid': float(ticker['bestBid']),
                            'ask': float(ticker['bestAsk'])
                        }
        except Exception as e:
            print(f"Ошибка KuCoin {symbol}: {e}")
        return None
    
    # ========== OKX ==========
    async def get_okx_price(self, symbol: str) -> Optional[Dict]:
        try:
            url = f"https://www.okx.com/api/v5/market/ticker?instId={symbol}"
            async with self.session.get(url, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data['code'] == '0' and data['data']:
                        ticker = data['data'][0]
                        return {
                            'exchange': 'OKX',
                            'symbol': symbol,
                            'price': float(ticker['last']),
                            'volume': float(ticker['vol24h']),
                            'bid': float(ticker['bidPx']),
                            'ask': float(ticker['askPx'])
                        }
        except Exception as e:
            print(f"Ошибка OKX {symbol}: {e}")
        return None
    
    # ========== ASTER (HUOBI) ==========
    async def get_aster_price(self, symbol: str) -> Optional[Dict]:
        try:
            url = f"https://api.huobi.pro/market/detail/merged?symbol={symbol}"
            async with self.session.get(url, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data['status'] == 'ok':
                        tick = data['tick']
                        return {
                            'exchange': 'Aster/Huobi',
                            'symbol': symbol,
                            'price': float(tick['close']),
                            'volume': float(tick['vol']),
                            'bid': float(tick['bid'][0]) if tick.get('bid') else 0,
                            'ask': float(tick['ask'][0]) if tick.get('ask') else 0
                        }
        except Exception as e:
            print(f"Ошибка Aster/Huobi {symbol}: {e}")
        return None
    
    # ========== MEXC ==========
    async def get_mexc_price(self, symbol: str) -> Optional[Dict]:
        try:
            url = f"https://api.mexc.com/api/v3/ticker/24hr?symbol={symbol}"
            async with self.session.get(url, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return {
                        'exchange': 'MEXC',
                        'symbol': symbol,
                        'price': float(data['lastPrice']),
                        'volume': float(data['volume']),
                        'bid': float(data['bidPrice']),
                        'ask': float(data['askPrice'])
                    }
        except Exception as e:
            print(f"Ошибка MEXC {symbol}: {e}")
        return None
    
    # ========== UNISWAP V3 ==========
    async def get_uniswap_price(self, token0: str, token1: str) -> Optional[Dict]:
        try:
            query = """
            {
              pools(
                first: 1,
                orderBy: totalValueLockedUSD,
                orderDirection: desc,
                where: {
                  token0: "%s",
                  token1: "%s"
                }
              ) {
                token0Price
                volumeUSD
              }
            }
            """ % (token0.lower(), token1.lower())
            
            url = "https://api.thegraph.com/subgraphs/name/uniswap/uniswap-v3"
            async with self.session.post(url, json={'query': query}, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get('data', {}).get('pools'):
                        pool = data['data']['pools'][0]
                        return {
                            'exchange': 'Uniswap V3',
                            'symbol': f'{token0[:6]}/{token1[:6]}',
                            'price': float(pool['token0Price']),
                            'volume': float(pool['volumeUSD']),
                            'bid': 0,
                            'ask': 0
                        }
        except Exception as e:
            print(f"Ошибка Uniswap: {e}")
        return None
    
    def calculate_arbitrage(self, prices: List[Dict]) -> List[Dict]:
        opportunities = []
        
        for i, price1 in enumerate(prices):
            for price2 in prices[i+1:]:
                if price1 and price2:
                    diff_percent = ((price2['price'] - price1['price']) / price1['price']) * 100
                    
                    opportunities.append({
                        'buy_exchange': price1['exchange'],
                        'sell_exchange': price2['exchange'],
                        'buy_price': price1['price'],
                        'sell_price': price2['price'],
                        'difference': abs(diff_percent),
                        'profit_direction': 'BUY' if diff_percent > 0 else 'SELL'
                    })
        
        return sorted(opportunities, key=lambda x: x['difference'], reverse=True)
    
    async def monitor_symbol(self, symbol_config: Dict):
        tasks = []
        
        if 'binance' in symbol_config:
            tasks.append(self.get_binance_price(symbol_config['binance']))
        if 'gateio' in symbol_config:
            tasks.append(self.get_gateio_price(symbol_config['gateio']))
        if 'bybit' in symbol_config:
            tasks.append(self.get_bybit_price(symbol_config['bybit']))
        if 'kucoin' in symbol_config:
            tasks.append(self.get_kucoin_price(symbol_config['kucoin']))
        if 'okx' in symbol_config:
            tasks.append(self.get_okx_price(symbol_config['okx']))
        if 'aster' in symbol_config:
            tasks.append(self.get_aster_price(symbol_config['aster']))
        if 'mexc' in symbol_config:
            tasks.append(self.get_mexc_price(symbol_config['mexc']))
        if 'uniswap' in symbol_config:
            token0, token1 = symbol_config['uniswap']
            tasks.append(self.get_uniswap_price(token0, token1))
        
        prices = await asyncio.gather(*tasks)
        prices = [p for p in prices if p is not None]
        
        return prices
    
    def format_telegram_message(self, symbol: str, prices: List[Dict], opportunities: List[Dict], threshold: float = 0.5) -> str:
        msg = f"🔄 <b>{symbol}</b>\n"
        msg += f"⏰ {datetime.now().strftime('%H:%M:%S')}\n\n"
        
        msg += "💰 <b>ЦЕНЫ НА БИРЖАХ:</b>\n"
        for price in sorted(prices, key=lambda x: x['price']):
            msg += f"├ <code>{price['exchange']:12}</code> ${price['price']:.4f}\n"
        
        # Фильтруем возможности по порогу
        filtered = [o for o in opportunities if o['difference'] >= threshold]
        
        if filtered:
            msg += f"\n🔥 <b>АРБИТРАЖ &gt; {threshold}%:</b>\n"
            for i, opp in enumerate(filtered[:3], 1):
                msg += f"\n{i}. <b>{opp['difference']:.2f}%</b> разница\n"
                msg += f"├ Купить:  {opp['buy_exchange']} @ ${opp['buy_price']:.4f}\n"
                msg += f"└ Продать: {opp['sell_exchange']} @ ${opp['sell_price']:.4f}\n"
        else:
            msg += f"\n✅ Нет арбитража &gt; {threshold}%\n"
        
        return msg

# Глобальный экземпляр бота
arbitrage_bot = ArbitrageBot()

# Конфигурация символов
SYMBOLS = {
    'BTC': {
        'name': 'BTC/USDT',
        'binance': 'BTCUSDT',
        'gateio': 'BTC_USDT',
        'bybit': 'BTCUSDT',
        'kucoin': 'BTC-USDT',
        'okx': 'BTC-USDT',
        'aster': 'btcusdt',
        'mexc': 'BTCUSDT',
        'uniswap': ('0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599', 
                   '0xdAC17F958D2ee523a2206206994597C13D831ec7')
    },
    'ETH': {
        'name': 'ETH/USDT',
        'binance': 'ETHUSDT',
        'gateio': 'ETH_USDT',
        'bybit': 'ETHUSDT',
        'kucoin': 'ETH-USDT',
        'okx': 'ETH-USDT',
        'aster': 'ethusdt',
        'mexc': 'ETHUSDT',
        'uniswap': ('0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2',
                   '0xdAC17F958D2ee523a2206206994597C13D831ec7')
    },
    'BNB': {
        'name': 'BNB/USDT',
        'binance': 'BNBUSDT',
        'gateio': 'BNB_USDT',
        'bybit': 'BNBUSDT',
        'kucoin': 'BNB-USDT',
        'okx': 'BNB-USDT',
        'mexc': 'BNBUSDT'
    },
    'SOL': {
        'name': 'SOL/USDT',
        'binance': 'SOLUSDT',
        'gateio': 'SOL_USDT',
        'bybit': 'SOLUSDT',
        'kucoin': 'SOL-USDT',
        'okx': 'SOL-USDT',
        'mexc': 'SOLUSDT'
    }
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📊 BTC/USDT", callback_data='check_BTC')],
        [InlineKeyboardButton("📊 ETH/USDT", callback_data='check_ETH')],
        [InlineKeyboardButton("📊 BNB/USDT", callback_data='check_BNB')],
        [InlineKeyboardButton("📊 SOL/USDT", callback_data='check_SOL')],
        [InlineKeyboardButton("🔄 Все монеты", callback_data='check_ALL')],
        [InlineKeyboardButton("🔔 Авто-мониторинг", callback_data='auto_monitor')],
        [InlineKeyboardButton("⛔ Остановить мониторинг", callback_data='stop_monitor')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🤖 <b>DEX-CEX Арбитражный бот</b>\n\n"
        "Отслеживаю разницу цен на:\n"
        "• Binance, Gate.io, Bybit\n"
        "• KuCoin, OKX, MEXC\n"
        "• Aster/Huobi, Uniswap V3\n\n"
        "Выберите действие:",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    await arbitrage_bot.init_session()
    
    if query.data == 'check_ALL':
        await query.edit_message_text("⏳ Проверяю все монеты...")
        
        for symbol_key, symbol_config in SYMBOLS.items():
            try:
                prices = await arbitrage_bot.monitor_symbol(symbol_config)
                if len(prices) >= 2:
                    opportunities = arbitrage_bot.calculate_arbitrage(prices)
                    msg = arbitrage_bot.format_telegram_message(
                        symbol_config['name'], prices, opportunities
                    )
                    await context.bot.send_message(
                        chat_id=query.message.chat_id,
                        text=msg,
                        parse_mode='HTML'
                    )
                await asyncio.sleep(1)
            except Exception as e:
                print(f"Ошибка {symbol_key}: {e}")
        
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data='back')]]
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="✅ Проверка завершена!",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    elif query.data.startswith('check_'):
        symbol_key = query.data.replace('check_', '')
        symbol_config = SYMBOLS[symbol_key]
        
        await query.edit_message_text(f"⏳ Проверяю {symbol_config['name']}...")
        
        try:
            prices = await arbitrage_bot.monitor_symbol(symbol_config)
            if len(prices) >= 2:
                opportunities = arbitrage_bot.calculate_arbitrage(prices)
                msg = arbitrage_bot.format_telegram_message(
                    symbol_config['name'], prices, opportunities
                )
                
                keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data='back')]]
                await query.edit_message_text(
                    msg,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='HTML'
                )
            else:
                await query.edit_message_text(
                    f"❌ Недостаточно данных для {symbol_config['name']}"
                )
        except Exception as e:
            await query.edit_message_text(f"❌ Ошибка: {str(e)}")
    
    elif query.data == 'auto_monitor':
        chat_id = query.message.chat_id
        if chat_id not in arbitrage_bot.monitoring or not arbitrage_bot.monitoring[chat_id]:
            arbitrage_bot.monitoring[chat_id] = True
            await query.edit_message_text(
                "🔔 <b>Авто-мониторинг включен!</b>\n\n"
                "Буду отправлять уведомления о разнице &gt; 0.5%\n"
                "Проверка каждые 60 секунд\n\n"
                "Для остановки нажмите 'Остановить мониторинг'",
                parse_mode='HTML'
            )
            
            context.job_queue.run_repeating(
                auto_monitor_job,
                interval=60,
                first=5,
                chat_id=chat_id,
                name=f'monitor_{chat_id}'
            )
        else:
            await query.answer("Мониторинг уже запущен!")
    
    elif query.data == 'stop_monitor':
        chat_id = query.message.chat_id
        arbitrage_bot.monitoring[chat_id] = False
        
        jobs = context.job_queue.get_jobs_by_name(f'monitor_{chat_id}')
        for job in jobs:
            job.schedule_removal()
        
        await query.edit_message_text("⛔ Мониторинг остановлен")
    
    elif query.data == 'back':
        keyboard = [
            [InlineKeyboardButton("📊 BTC/USDT", callback_data='check_BTC')],
            [InlineKeyboardButton("📊 ETH/USDT", callback_data='check_ETH')],
            [InlineKeyboardButton("📊 BNB/USDT", callback_data='check_BNB')],
            [InlineKeyboardButton("📊 SOL/USDT", callback_data='check_SOL')],
            [InlineKeyboardButton("🔄 Все монеты", callback_data='check_ALL')],
            [InlineKeyboardButton("🔔 Авто-мониторинг", callback_data='auto_monitor')],
            [InlineKeyboardButton("⛔ Остановить мониторинг", callback_data='stop_monitor')]
        ]
        await query.edit_message_text(
            "🤖 <b>DEX-CEX Арбитражный бот</b>\n\n"
            "Выберите действие:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )

async def auto_monitor_job(context: ContextTypes.DEFAULT_TYPE):
    chat_id = context.job.chat_id
    
    if not arbitrage_bot.monitoring.get(chat_id, False):
        return
    
    await arbitrage_bot.init_session()
    
    for symbol_key, symbol_config in SYMBOLS.items():
        try:
            prices = await arbitrage_bot.monitor_symbol(symbol_config)
            if len(prices) >= 2:
                opportunities = arbitrage_bot.calculate_arbitrage(prices)
                
                # Отправляем только если есть разница > 0.5%
                if any(o['difference'] >= 0.5 for o in opportunities):
                    msg = arbitrage_bot.format_telegram_message(
                        symbol_config['name'], prices, opportunities, threshold=0.5
                    )
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text=msg,
                        parse_mode='HTML'
                    )
        except Exception as e:
            print(f"Ошибка мониторинга {symbol_key}: {e}")

def main():
    # Получаем токен из переменной окружения
    TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    
    if not TOKEN:
        print("❌ ОШИБКА: Установите TELEGRAM_BOT_TOKEN в переменные окружения!")
        return
    
    # Создаем приложение
    application = Application.builder().token(TOKEN).build()
    
    # Добавляем обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    
    print("🚀 Бот запущен!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
