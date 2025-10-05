"""
Binance data downloader module for fetching cryptocurrency historical data
"""

import requests
import pandas as pd
from datetime import datetime, timedelta
import time
from typing import Optional, Callable

class BinanceDataDownloader:
    """Download historical cryptocurrency data from Binance (Spot and Futures)"""

    # API endpoints
    SPOT_KLINES_URL = "https://api.binance.com/api/v3/klines"
    FUTURES_KLINES_URL = "https://fapi.binance.com/fapi/v1/klines"
    SPOT_EXCHANGE_INFO_URL = "https://api.binance.com/api/v3/exchangeInfo"
    FUTURES_EXCHANGE_INFO_URL = "https://fapi.binance.com/fapi/v1/exchangeInfo"

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

    def __init__(self, market_type='auto'):
        """
        Initialize downloader

        Args:
            market_type: 'spot', 'futures', or 'auto' (tries spot first, then futures)
        """
        self.session = requests.Session()
        self.market_type = market_type.lower()

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
        # Determine which market to use and verify symbol exists
        market_to_use = None
        klines_url = None

        if self.market_type == 'auto':
            # Try spot first, then futures
            print(f"Auto-detecting market for {symbol}...")
            if self._verify_symbol(symbol, 'spot'):
                market_to_use = 'spot'
                klines_url = self.SPOT_KLINES_URL
                print(f"✓ {symbol} found on Spot market")
            elif self._verify_symbol(symbol, 'futures'):
                market_to_use = 'futures'
                klines_url = self.FUTURES_KLINES_URL
                print(f"✓ {symbol} found on Futures market")
            else:
                raise ValueError(f"Symbol {symbol} not found on Binance Spot or Futures markets")
        elif self.market_type == 'spot':
            if not self._verify_symbol(symbol, 'spot'):
                raise ValueError(f"Symbol {symbol} not found on Binance Spot market")
            market_to_use = 'spot'
            klines_url = self.SPOT_KLINES_URL
        elif self.market_type == 'futures':
            if not self._verify_symbol(symbol, 'futures'):
                raise ValueError(f"Symbol {symbol} not found on Binance Futures market")
            market_to_use = 'futures'
            klines_url = self.FUTURES_KLINES_URL
        else:
            raise ValueError(f"Invalid market_type: {self.market_type}. Use 'spot', 'futures', or 'auto'")

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
                response = self.session.get(klines_url, params=params, timeout=30)

                if response.status_code == 200:
                    klines = response.json()
                    if not klines:
                        # If first request returns no data, try binary search to find actual start date
                        if request_count == 1 and current_start < end_ms:
                            print(f"No data available from {datetime.fromtimestamp(current_start/1000)}")
                            print(f"Searching for actual listing date...")

                            # Binary search for the first available data
                            actual_start = self._find_first_available_date(symbol, interval, current_start, end_ms, klines_url)
                            if actual_start:
                                print(f"Found data starting from {datetime.fromtimestamp(actual_start/1000)}")
                                current_start = actual_start
                                # Reset counters
                                total_requests = ((end_ms - current_start) // (limit * interval_ms)) + 1
                                request_count = 0
                                continue
                            else:
                                print(f"No data found for {symbol} in the entire requested range")
                                break
                        # Otherwise, we've reached the end of available data
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
                elif response.status_code == 400:
                    # Bad request - likely invalid symbol or parameters
                    error_msg = f"Invalid request for {symbol}: {response.text}"
                    print(error_msg)
                    raise ValueError(error_msg)
                else:
                    error_msg = f"API Error {response.status_code}: {response.text}"
                    print(error_msg)
                    raise ValueError(error_msg)

            except requests.exceptions.Timeout:
                print(f"Request timeout for {symbol}")
                raise ValueError(f"Request timeout for {symbol}")
            except requests.exceptions.RequestException as e:
                print(f"Network error: {e}")
                raise ValueError(f"Network error: {e}")
            except Exception as e:
                print(f"Request error: {e}")
                raise

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

    def _verify_symbol(self, symbol: str, market: str) -> bool:
        """
        Verify if a symbol exists on the specified market

        Args:
            symbol: Trading pair symbol (e.g., 'BTCUSDT')
            market: 'spot' or 'futures'

        Returns:
            True if symbol exists, False otherwise
        """
        try:
            if market == 'spot':
                url = self.SPOT_EXCHANGE_INFO_URL
            elif market == 'futures':
                url = self.FUTURES_EXCHANGE_INFO_URL
            else:
                return False

            response = self.session.get(url, params={'symbol': symbol}, timeout=10)

            if response.status_code == 200:
                data = response.json()
                # Check if symbol exists in response
                if 'symbols' in data and len(data['symbols']) > 0:
                    return True
            return False

        except Exception as e:
            print(f"Error verifying symbol on {market}: {e}")
            return False

    def _find_first_available_date(self, symbol: str, interval: str, start_ms: int, end_ms: int, klines_url: str) -> Optional[int]:
        """
        Find the first date with available data by fetching the earliest candle.
        Returns the timestamp in milliseconds, or None if no data found.
        """
        # Request from timestamp 0 (epoch) to get the first available candle
        params = {
            'symbol': symbol,
            'interval': interval,
            'startTime': 0,  # Start from epoch (1970)
            'limit': 1  # Get just the first candle
        }

        try:
            response = self.session.get(klines_url, params=params, timeout=10)
            if response.status_code == 200:
                klines = response.json()
                if klines and len(klines) > 0:
                    # First element is the timestamp
                    first_candle_time = klines[0][0]
                    print(f"First available candle: {datetime.fromtimestamp(first_candle_time/1000)}")
                    return first_candle_time
        except Exception as e:
            print(f"Error finding first date: {e}")

        return None

    def _get_interval_ms(self, interval: str) -> int:
        """Convert interval string to milliseconds - supports custom intervals"""
        # First check predefined intervals
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

        if interval in interval_map:
            return interval_map[interval]

        # Try to parse custom interval (e.g., "2d", "10m", "5h")
        import re
        match = re.match(r'^(\d+)([mhdwM])$', interval)
        if match:
            value = int(match.group(1))
            unit = match.group(2)

            unit_ms = {
                'm': 60 * 1000,                    # minute
                'h': 60 * 60 * 1000,               # hour
                'd': 24 * 60 * 60 * 1000,          # day
                'w': 7 * 24 * 60 * 60 * 1000,      # week
                'M': 30 * 24 * 60 * 60 * 1000      # month (approximate)
            }

            return value * unit_ms.get(unit, 24 * 60 * 60 * 1000)

        # Default to 1 day if cannot parse
        return 24 * 60 * 60 * 1000

    def resample_ohlc(self, df: pd.DataFrame, target_timeframe: str) -> pd.DataFrame:
        """
        Resample OHLC data to a custom timeframe

        Args:
            df: DataFrame with OHLC data and Date column
            target_timeframe: Target timeframe (e.g., '2d', '5d', '90m', '10m')

        Returns:
            Resampled DataFrame
        """
        # Make a copy to avoid modifying original
        df_copy = df.copy()

        # Find the date column (could be 'Date', 'date', 'timestamp', etc.)
        date_column = None
        for col in df_copy.columns:
            if col.lower() in ['date', 'timestamp', 'time', 'datetime']:
                date_column = col
                break

        if date_column is None:
            raise ValueError("No date column found in DataFrame. Expected column named 'Date', 'timestamp', or 'time'")

        # Ensure date column is datetime and set as index
        df_copy[date_column] = pd.to_datetime(df_copy[date_column])
        df_copy.set_index(date_column, inplace=True)

        # Map custom timeframe to pandas frequency
        # Convert formats like '2d' to '2D', '90m' to '90T', etc.
        import re
        match = re.match(r'^(\d+)([mhdwM])$', target_timeframe)
        if not match:
            raise ValueError(f"Invalid timeframe format: {target_timeframe}")

        value = match.group(1)
        unit = match.group(2)

        # Map to pandas frequency codes
        unit_map = {
            'm': 'T',  # minutes -> T (for Time)
            'h': 'H',  # hours
            'd': 'D',  # days
            'w': 'W',  # weeks
            'M': 'M'   # months
        }

        pandas_freq = f"{value}{unit_map[unit]}"

        # Build aggregation dict based on available columns
        agg_dict = {}

        # Check column names (case-insensitive)
        columns_lower = {col.lower(): col for col in df_copy.columns}

        if 'open' in columns_lower:
            agg_dict[columns_lower['open']] = 'first'
        if 'high' in columns_lower:
            agg_dict[columns_lower['high']] = 'max'
        if 'low' in columns_lower:
            agg_dict[columns_lower['low']] = 'min'
        if 'close' in columns_lower:
            agg_dict[columns_lower['close']] = 'last'
        if 'volume' in columns_lower:
            agg_dict[columns_lower['volume']] = 'sum'

        if not agg_dict:
            raise ValueError("No OHLC columns found in DataFrame")

        # Resample with proper OHLC aggregation
        resampled = df_copy.resample(pandas_freq).agg(agg_dict)

        # Drop any NaN rows (can occur at boundaries)
        resampled = resampled.dropna()

        # Reset index to make date a column again
        resampled.reset_index(inplace=True)

        # Rename the index column back to original name
        if resampled.columns[0] != date_column:
            resampled.rename(columns={resampled.columns[0]: date_column}, inplace=True)

        return resampled

    def get_base_timeframe(self, target_timeframe: str) -> str:
        """
        Determine the best Binance-supported timeframe to download
        for resampling to the target timeframe

        Args:
            target_timeframe: Desired timeframe (e.g., '2d', '90m', '10m')

        Returns:
            Best available Binance timeframe to use as base
        """
        import re
        match = re.match(r'^(\d+)([mhdwM])$', target_timeframe)
        if not match:
            return '1d'  # Default fallback

        value = int(match.group(1))
        unit = match.group(2)

        # Binance supported intervals
        binance_intervals = {
            'm': [1, 3, 5, 15, 30],
            'h': [1, 2, 4, 6, 8, 12],
            'd': [1, 3],
            'w': [1],
            'M': [1]
        }

        # If it's already a supported interval, return it
        if unit in binance_intervals and value in binance_intervals[unit]:
            return target_timeframe

        # Find the best base interval (largest that divides evenly into target)
        supported = binance_intervals.get(unit, [1])

        # Find largest supported interval that's smaller than or equal to target
        base = 1
        for interval in sorted(supported, reverse=True):
            if interval <= value and value % interval == 0:
                base = interval
                break

        # If no good divisor found, use smallest available
        if base == 1 and supported:
            base = min(supported)

        return f"{base}{unit}"

    def save_to_csv(self, df: pd.DataFrame, filename: str):
        """Save DataFrame to CSV file"""
        df.to_csv(filename, index=False)
        print(f"Data saved to {filename}")