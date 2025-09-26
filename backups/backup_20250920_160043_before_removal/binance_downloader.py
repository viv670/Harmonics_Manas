"""
Binance data downloader module for fetching cryptocurrency historical data
"""

import requests
import pandas as pd
from datetime import datetime, timedelta
import time
from typing import Optional, Callable

class BinanceDataDownloader:
    """Download historical cryptocurrency data from Binance"""

    BASE_URL = "https://api.binance.com/api/v3/klines"

    # Popular cryptocurrency pairs
    POPULAR_SYMBOLS = [
        'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'XRPUSDT',
        'ADAUSDT', 'DOGEUSDT', 'AVAXUSDT', 'SHIBUSDT', 'DOTUSDT',
        'MATICUSDT', 'LTCUSDT', 'LINKUSDT', 'ATOMUSDT', 'UNIUSDT',
        'XLMUSDT', 'ETCUSDT', 'FILUSDT', 'APTUSDT', 'ARBUSDT'
    ]

    # Available timeframes
    TIMEFRAMES = {
        '1m': '1 minute',
        '3m': '3 minutes',
        '5m': '5 minutes',
        '15m': '15 minutes',
        '30m': '30 minutes',
        '1h': '1 hour',
        '2h': '2 hours',
        '4h': '4 hours',
        '6h': '6 hours',
        '8h': '8 hours',
        '12h': '12 hours',
        '1d': '1 day',
        '3d': '3 days',
        '1w': '1 week',
        '1M': '1 month'
    }

    def __init__(self):
        self.session = requests.Session()

    def get_available_symbols(self) -> list:
        """Get all available trading symbols from Binance"""
        try:
            response = self.session.get("https://api.binance.com/api/v3/exchangeInfo")
            if response.status_code == 200:
                data = response.json()
                symbols = [s['symbol'] for s in data['symbols'] if s['status'] == 'TRADING']
                # Filter for USDT pairs
                usdt_symbols = [s for s in symbols if s.endswith('USDT')]
                return sorted(usdt_symbols)
        except Exception as e:
            print(f"Error fetching symbols: {e}")
        return self.POPULAR_SYMBOLS

    def download_data(self,
                     symbol: str,
                     interval: str,
                     start_date: datetime,
                     end_date: datetime,
                     progress_callback: Optional[Callable[[int, str], None]] = None) -> pd.DataFrame:
        """
        Download historical kline data from Binance

        Args:
            symbol: Trading pair symbol (e.g., 'BTCUSDT')
            interval: Timeframe (e.g., '1d', '4h', '1h')
            start_date: Start date for data
            end_date: End date for data
            progress_callback: Optional callback for progress updates (percent, message)

        Returns:
            DataFrame with OHLCV data
        """
        all_klines = []

        # Convert dates to milliseconds
        start_ms = int(start_date.timestamp() * 1000)
        end_ms = int(end_date.timestamp() * 1000)

        # Binance limit is 1000 candles per request
        limit = 1000

        # Calculate interval in milliseconds
        interval_ms = self._get_interval_ms(interval)

        current_start = start_ms
        total_requests = ((end_ms - start_ms) // (limit * interval_ms)) + 1
        request_count = 0

        while current_start < end_ms:
            request_count += 1

            if progress_callback:
                progress = int((request_count / total_requests) * 100)
                progress_callback(progress, f"Downloading {symbol} data... ({request_count}/{total_requests})")

            params = {
                'symbol': symbol,
                'interval': interval,
                'startTime': current_start,
                'endTime': min(current_start + limit * interval_ms, end_ms),
                'limit': limit
            }

            try:
                response = self.session.get(self.BASE_URL, params=params)

                if response.status_code == 200:
                    klines = response.json()
                    if not klines:
                        break
                    all_klines.extend(klines)

                    # Update start time for next request
                    current_start = klines[-1][0] + interval_ms

                    # Rate limit: Binance allows 1200 requests per minute
                    time.sleep(0.1)

                elif response.status_code == 429:
                    # Rate limited, wait and retry
                    if progress_callback:
                        progress_callback(request_count, "Rate limited, waiting...")
                    time.sleep(5)
                    continue
                else:
                    print(f"Error: {response.status_code} - {response.text}")
                    break

            except Exception as e:
                print(f"Request error: {e}")
                break

        if not all_klines:
            raise ValueError(f"No data retrieved for {symbol}")

        # Convert to DataFrame
        df = pd.DataFrame(all_klines, columns=[
            'time', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_volume', 'trades', 'taker_buy_base',
            'taker_buy_quote', 'ignore'
        ])

        # Convert types
        df['time'] = pd.to_datetime(df['time'], unit='ms')
        df['open'] = df['open'].astype(float)
        df['high'] = df['high'].astype(float)
        df['low'] = df['low'].astype(float)
        df['close'] = df['close'].astype(float)
        df['volume'] = df['volume'].astype(float)

        # Keep only OHLCV columns
        df = df[['time', 'open', 'high', 'low', 'close', 'volume']]

        # Remove duplicates
        df = df.drop_duplicates(subset=['time'])

        # Sort by time
        df = df.sort_values('time')

        if progress_callback:
            progress_callback(100, f"Downloaded {len(df)} candles for {symbol}")

        return df

    def _get_interval_ms(self, interval: str) -> int:
        """Convert interval string to milliseconds"""
        interval_map = {
            '1m': 60 * 1000,
            '3m': 3 * 60 * 1000,
            '5m': 5 * 60 * 1000,
            '15m': 15 * 60 * 1000,
            '30m': 30 * 60 * 1000,
            '1h': 60 * 60 * 1000,
            '2h': 2 * 60 * 60 * 1000,
            '4h': 4 * 60 * 60 * 1000,
            '6h': 6 * 60 * 60 * 1000,
            '8h': 8 * 60 * 60 * 1000,
            '12h': 12 * 60 * 60 * 1000,
            '1d': 24 * 60 * 60 * 1000,
            '3d': 3 * 24 * 60 * 60 * 1000,
            '1w': 7 * 24 * 60 * 60 * 1000,
            '1M': 30 * 24 * 60 * 60 * 1000
        }
        return interval_map.get(interval, 24 * 60 * 60 * 1000)

    def save_to_csv(self, df: pd.DataFrame, filename: str):
        """Save DataFrame to CSV file"""
        df.to_csv(filename, index=False)
        print(f"Data saved to {filename}")