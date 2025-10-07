"""
Data Service

Business logic for data loading, processing, and management.
"""

import pandas as pd
import yfinance as yf
from typing import Optional, List, Dict
from datetime import datetime, timedelta
from pathlib import Path
import logging

from exceptions import DataError, InvalidDataError, MissingDataError, DataDownloadError
from logging_config import get_logger


class DataService:
    """
    Service for data operations.

    Handles data loading, validation, downloading, and caching.
    """

    REQUIRED_COLUMNS = ['Open', 'High', 'Low', 'Close']
    VOLUME_COLUMN = 'Volume'

    def __init__(self, data_dir: str = 'data'):
        """
        Initialize data service.

        Args:
            data_dir: Directory for data files
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        self.logger = get_logger()
        self.loaded_data = {}

    def load_csv(
        self,
        file_path: str,
        validate: bool = True,
        date_column: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Load data from CSV file.

        Args:
            file_path: Path to CSV file
            validate: Whether to validate data
            date_column: Column to use as index (if not already indexed)

        Returns:
            DataFrame with OHLC data

        Raises:
            DataError: If file cannot be loaded or data is invalid
        """
        try:
            self.logger.info(f"Loading data from {file_path}")

            # Load CSV
            df = pd.read_csv(file_path)

            # Set date index if specified
            if date_column and date_column in df.columns:
                df[date_column] = pd.to_datetime(df[date_column])
                df.set_index(date_column, inplace=True)

            # Validate if requested
            if validate:
                self.validate_ohlc_data(df)

            self.logger.info(f"Loaded {len(df)} rows from {file_path}")
            return df

        except FileNotFoundError:
            raise MissingDataError(f"File not found: {file_path}")
        except Exception as e:
            raise DataError(f"Failed to load CSV: {e}") from e

    def download_data(
        self,
        symbol: str,
        interval: str = '1h',
        period: str = '1mo',
        save: bool = True
    ) -> pd.DataFrame:
        """
        Download data from Yahoo Finance.

        Args:
            symbol: Trading symbol
            interval: Data interval (1m, 5m, 15m, 1h, 4h, 1d, etc.)
            period: Data period (1d, 5d, 1mo, 3mo, 1y, etc.)
            save: Whether to save to CSV

        Returns:
            DataFrame with OHLC data

        Raises:
            DataDownloadError: If download fails
        """
        try:
            self.logger.info(f"Downloading {symbol} data ({interval}, {period})")

            # Download from yfinance
            ticker = yf.Ticker(symbol)
            df = ticker.history(period=period, interval=interval)

            if df.empty:
                raise DataDownloadError(f"No data returned for {symbol}")

            # Validate
            self.validate_ohlc_data(df)

            # Save if requested
            if save:
                filename = f"{symbol.lower()}_{interval}.csv"
                save_path = self.data_dir / filename
                df.to_csv(save_path)
                self.logger.info(f"Saved data to {save_path}")

            self.logger.info(f"Downloaded {len(df)} rows for {symbol}")
            return df

        except Exception as e:
            raise DataDownloadError(f"Failed to download data for {symbol}: {e}") from e

    def validate_ohlc_data(self, df: pd.DataFrame):
        """
        Validate OHLC data.

        Args:
            df: DataFrame to validate

        Raises:
            InvalidDataError: If data is invalid
        """
        # Check required columns
        missing_cols = [col for col in self.REQUIRED_COLUMNS if col not in df.columns]
        if missing_cols:
            raise InvalidDataError(f"Missing required columns: {missing_cols}")

        # Check for empty data
        if df.empty:
            raise InvalidDataError("DataFrame is empty")

        # Validate OHLC relationship: High >= Open, Close, Low <= Open, Close
        invalid_rows = []

        for idx in range(len(df)):
            row = df.iloc[idx]
            high = row['High']
            low = row['Low']
            open_price = row['Open']
            close = row['Close']

            if not (low <= open_price <= high and low <= close <= high):
                invalid_rows.append(idx)

        if invalid_rows:
            self.logger.warning(f"Found {len(invalid_rows)} invalid OHLC rows")
            # Don't raise error, just log warning

        self.logger.debug(f"Data validation passed: {len(df)} rows")

    def resample_data(
        self,
        df: pd.DataFrame,
        timeframe: str
    ) -> pd.DataFrame:
        """
        Resample data to different timeframe.

        Args:
            df: Source DataFrame
            timeframe: Target timeframe (e.g., '4h', '1d', '1w')

        Returns:
            Resampled DataFrame
        """
        try:
            self.logger.info(f"Resampling to {timeframe}")

            # Ensure datetime index
            if not isinstance(df.index, pd.DatetimeIndex):
                raise InvalidDataError("Index must be DatetimeIndex for resampling")

            # Resample
            resampled = df.resample(timeframe).agg({
                'Open': 'first',
                'High': 'max',
                'Low': 'min',
                'Close': 'last',
                'Volume': 'sum'
            })

            # Drop NaN rows
            resampled = resampled.dropna()

            self.logger.info(f"Resampled to {len(resampled)} rows")
            return resampled

        except Exception as e:
            raise DataError(f"Resampling failed: {e}") from e

    def get_latest_data(
        self,
        symbol: str,
        interval: str = '1h',
        bars: int = 100
    ) -> pd.DataFrame:
        """
        Get latest N bars for a symbol.

        Args:
            symbol: Trading symbol
            interval: Data interval
            bars: Number of bars

        Returns:
            DataFrame with latest bars
        """
        # Calculate period based on bars and interval
        interval_map = {
            '1m': timedelta(minutes=1),
            '5m': timedelta(minutes=5),
            '15m': timedelta(minutes=15),
            '1h': timedelta(hours=1),
            '4h': timedelta(hours=4),
            '1d': timedelta(days=1),
        }

        delta = interval_map.get(interval, timedelta(hours=1))
        total_time = delta * bars * 1.5  # Add buffer

        # Determine period string
        if total_time.days > 365:
            period = '2y'
        elif total_time.days > 60:
            period = '3mo'
        elif total_time.days > 5:
            period = '1mo'
        else:
            period = '5d'

        # Download and return latest bars
        df = self.download_data(symbol, interval, period, save=False)
        return df.tail(bars)

    def merge_data(
        self,
        dfs: List[pd.DataFrame],
        how: str = 'outer'
    ) -> pd.DataFrame:
        """
        Merge multiple DataFrames.

        Args:
            dfs: List of DataFrames
            how: Merge method ('outer', 'inner', 'left', 'right')

        Returns:
            Merged DataFrame
        """
        if not dfs:
            return pd.DataFrame()

        if len(dfs) == 1:
            return dfs[0]

        # Merge all DataFrames
        result = dfs[0]
        for df in dfs[1:]:
            result = pd.merge(
                result, df,
                left_index=True,
                right_index=True,
                how=how,
                suffixes=('', '_dup')
            )

        # Remove duplicate columns
        result = result.loc[:, ~result.columns.str.endswith('_dup')]

        return result

    def calculate_indicators(
        self,
        df: pd.DataFrame,
        indicators: List[str] = None
    ) -> pd.DataFrame:
        """
        Calculate technical indicators.

        Args:
            df: OHLC DataFrame
            indicators: List of indicators to calculate

        Returns:
            DataFrame with indicators added
        """
        if indicators is None:
            indicators = ['SMA_20', 'SMA_50', 'EMA_20']

        df_copy = df.copy()

        for indicator in indicators:
            if indicator.startswith('SMA_'):
                period = int(indicator.split('_')[1])
                df_copy[indicator] = df['Close'].rolling(window=period).mean()

            elif indicator.startswith('EMA_'):
                period = int(indicator.split('_')[1])
                df_copy[indicator] = df['Close'].ewm(span=period, adjust=False).mean()

            elif indicator == 'RSI':
                # Simple RSI calculation
                delta = df['Close'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                rs = gain / loss
                df_copy['RSI'] = 100 - (100 / (1 + rs))

        return df_copy

    def get_data_info(self, df: pd.DataFrame) -> Dict:
        """
        Get information about DataFrame.

        Args:
            df: DataFrame to analyze

        Returns:
            Dictionary with data info
        """
        return {
            'rows': len(df),
            'columns': list(df.columns),
            'start_date': df.index[0] if len(df) > 0 else None,
            'end_date': df.index[-1] if len(df) > 0 else None,
            'missing_values': df.isnull().sum().to_dict(),
            'price_range': {
                'high': df['High'].max() if 'High' in df else None,
                'low': df['Low'].min() if 'Low' in df else None
            }
        }


if __name__ == "__main__":
    print("Testing Data Service...")
    print()

    service = DataService()

    # Test download
    try:
        df = service.download_data('AAPL', '1d', '1mo', save=False)
        print(f"Downloaded {len(df)} rows")

        # Get info
        info = service.get_data_info(df)
        print(f"Date range: {info['start_date']} to {info['end_date']}")
        print(f"Price range: {info['price_range']}")

    except Exception as e:
        print(f"Error: {e}")

    print()
    print("✅ Data Service ready!")
