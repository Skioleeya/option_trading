import logging
import pandas as pd
from typing import Optional, Any, Dict, List
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# US Eastern Time zone - 符合Python 3.13现代语法
ET = ZoneInfo("America/New_York")


class RedisDataReader:
    """
    Redis data reader for breadth momentum data
    Provides high-level data access methods for the monitoring system
    """

    def __init__(self, redis_client):
        """
        Initialize Redis data reader

        Args:
            redis_client: RedisClient instance
        """
        self.redis_client = redis_client

    def is_available(self) -> bool:
        """
        Check if Redis client is available and connected

        Returns:
            bool: True if available, False otherwise
        """
        try:
            return self.redis_client.is_connected()
        except Exception as e:
            logging.error(f"Error checking Redis availability: {e}")
            return False

    def get_data_count(self) -> int:
        """
        Get total number of stored records

        Returns:
            int: Total number of records in Redis
        """
        try:
            return self.redis_client.get_data_count()
        except Exception as e:
            logging.error(f"Error getting data count: {e}")
            return 0

    def read_latest_data(self, minutes: int = 1440) -> pd.DataFrame:
        """
        Read latest data for the specified number of minutes

        Args:
            minutes: Number of minutes of data to retrieve (default: 1440 = 24 hours)

        Returns:
            pd.DataFrame: DataFrame with breadth data
        """
        try:
            if not self.is_available():
                logging.warning("Redis client not available")
                return pd.DataFrame()

            # Calculate time range
            end_time = datetime.now(ET)
            start_time = end_time - timedelta(minutes=minutes)

            # Get data from Redis
            data = self.redis_client.get_breadth_data_range(
                start_time=start_time,
                end_time=end_time
            )

            if not data:
                logging.info(f"No data found for the last {minutes} minutes")
                return pd.DataFrame()

            # Convert to DataFrame
            df = pd.DataFrame(data)

            # Convert timestamp strings to datetime with proper timezone handling
            # Timestamps are stored as ISO format and may already be timezone-aware
            if 'timestamp' in df.columns:
                df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
                # Ensure all timestamps are in Eastern Time
                if df['timestamp'].dt.tz is None:
                    df['timestamp'] = df['timestamp'].dt.tz_localize(ET)
                else:
                    df['timestamp'] = df['timestamp'].dt.tz_convert(ET)

            logging.info(f"Retrieved {len(df)} records for the last {minutes} minutes")
            return df

        except Exception as e:
            logging.error(f"Error reading latest data: {e}")
            return pd.DataFrame()

    def read_historical_date(self, date_obj) -> pd.DataFrame:
        """
        Read all data for a specific historical date

        Args:
            date_obj: datetime.date object representing the date to retrieve

        Returns:
            pd.DataFrame: DataFrame with breadth data for the specified date
        """
        try:
            if not self.is_available():
                logging.warning("Redis client not available")
                return pd.DataFrame()

            # Format date as YYYY-MM-DD string
            date_str = date_obj.strftime("%Y-%m-%d")

            # Get data for the specific date
            data = self.redis_client.get_date_data(date_str)

            if not data:
                logging.info(f"No data found for date {date_str}")
                return pd.DataFrame()

            # Convert to DataFrame
            df = pd.DataFrame(data)

            # Convert timestamp strings to datetime with proper timezone handling
            # Timestamps are stored as ISO format and may already be timezone-aware
            if 'timestamp' in df.columns:
                df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
                # Ensure all timestamps are in Eastern Time
                if df['timestamp'].dt.tz is None:
                    df['timestamp'] = df['timestamp'].dt.tz_localize(ET)
                else:
                    df['timestamp'] = df['timestamp'].dt.tz_convert(ET)

            logging.info(f"Retrieved {len(df)} records for date {date_str}")
            return df

        except Exception as e:
            logging.error(f"Error reading historical data for {date_obj}: {e}")
            return pd.DataFrame()

    def read_trading_dates(self) -> List[str]:
        """
        Get all available trading dates

        Returns:
            List[str]: List of trading dates in YYYY-MM-DD format
        """
        try:
            if not self.is_available():
                logging.warning("Redis client not available")
                return []

            return self.redis_client.get_trading_dates()

        except Exception as e:
            logging.error(f"Error reading trading dates: {e}")
            return []
