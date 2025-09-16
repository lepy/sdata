import pandas as pd
import io
import base64
from typing import Any, Dict, List, Optional
import logging
from sdata.base import Base
logger = logging.getLogger(__name__)

class DataFrameGroup(Base):
    """
    A derived class from Base that manages a group of Pandas DataFrames.
    Stores DataFrames in self.data['dataframes'] as a dictionary where:
    - Keys are unique identifiers for the DataFrames (e.g., names or custom keys).
    - Values are dictionaries with:
      - 'df': the Pandas DataFrame object.
      - 'column_metadata': a dict where keys are column names (colname), and values are dicts with 'label' (str) and 'unit' (str).

    For serialization, DataFrames are converted to Parquet bytes (base64-encoded for JSON compatibility),
    and column_metadata is serialized as a nested dict.
    """

    def __init__(self, **kwargs: Any) -> None:
        """
        Initialize DataFrameGroup.

        :param kwargs: Keyword arguments passed to Base.__init__.
        """
        super().__init__(**kwargs)
        # Initialize the dataframes dictionary if not already present in data
        if 'dataframes' not in self.data:
            self.data['dataframes'] = {}

    def add_dataframe(
            self,
            key: str,
            df: pd.DataFrame,
            column_metadata: Optional[Dict[str, Dict[str, str]]] = None,
            overwrite: bool = False
    ) -> None:
        """
        Add a Pandas DataFrame to the group along with optional column metadata.

        :param key: Unique key for the DataFrame.
        :param df: The Pandas DataFrame to add.
        :param column_metadata: Optional dict of column metadata, e.g., {colname: {'label': 'Description', 'unit': 'kg'}}.
          If provided, must include all columns in df; colname is the key.
        :param overwrite: If True, overwrite existing entry with the same key.
        :raises ValueError: If key already exists and overwrite is False, or if column_metadata doesn't match df columns.
        """
        if key in self.data['dataframes'] and not overwrite:
            raise ValueError(f"DataFrame with key '{key}' already exists. Set overwrite=True to replace.")

        if column_metadata is not None:
            if set(column_metadata.keys()) != set(df.columns):
                raise ValueError("column_metadata keys must match the DataFrame's columns exactly.")
            for meta in column_metadata.values():
                if not all(k in meta for k in ['label', 'unit']):
                    raise ValueError("Each column_metadata entry must have 'label' and 'unit' keys.")

        self.data['dataframes'][key] = {
            'df': df,
            'column_metadata': column_metadata or {col: {'label': '', 'unit': ''} for col in df.columns}
        }
        logger.debug(f"Added DataFrame '{key}' to {self.sname}")

    def get_dataframe(self, key: str) -> Optional[pd.DataFrame]:
        """
        Retrieve a DataFrame by key.

        :param key: The unique key for the DataFrame.
        :return: The Pandas DataFrame if found, else None.
        """
        entry = self.data['dataframes'].get(key)
        if entry:
            return entry['df']
        return None

    def get_column_metadata(self, key: str) -> Optional[Dict[str, Dict[str, str]]]:
        """
        Retrieve column metadata for a DataFrame by key.
        Each entry is {colname: {'label': str, 'unit': str}}.

        :param key: The unique key for the DataFrame.
        :return: Dict of column metadata if found, else None.
        """
        entry = self.data['dataframes'].get(key)
        if entry:
            return entry['column_metadata']
        return None

    def remove_dataframe(self, key: str) -> None:
        """
        Remove a DataFrame and its metadata from the group by key.

        :param key: The unique key for the DataFrame.
        :raises KeyError: If the key does not exist.
        """
        if key not in self.data['dataframes']:
            raise KeyError(f"DataFrame with key '{key}' not found.")
        del self.data['dataframes'][key]
        logger.debug(f"Removed DataFrame '{key}' from {self.sname}")

    def list_dataframes(self) -> List[str]:
        """
        List all DataFrame keys in the group.

        :return: List of DataFrame keys.
        """
        return list(self.data['dataframes'].keys())

    def to_dict(self) -> Dict[str, Any]:
        """
        Extend Base.to_dict to serialize DataFrames to base64-encoded Parquet bytes
        and include column_metadata as a nested dict.
        This ensures compatibility with JSON serialization.
        """
        data_copy = self.data.copy()
        if 'dataframes' in data_copy:
            serialized_dfs = {}
            for key, entry in data_copy['dataframes'].items():
                df = entry['df']
                bytes_io = io.BytesIO()
                df.to_parquet(bytes_io, engine='pyarrow')
                parquet_bytes = bytes_io.getvalue()
                serialized_dfs[key] = {
                    'parquet': base64.b64encode(parquet_bytes).decode('utf-8'),
                    'column_metadata': entry['column_metadata']
                }
            data_copy['dataframes'] = serialized_dfs
        result = super().to_dict()
        result['data'] = data_copy
        return result

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> 'DataFrameGroup':
        """
        Create a DataFrameGroup instance from a dictionary.
        Deserializes base64-encoded Parquet bytes back to Pandas DataFrames
        and restores column_metadata.
        """
        instance = super().from_dict(d)
        if 'dataframes' in instance.data:
            deserialized_dfs = {}
            for key, serialized_entry in instance.data['dataframes'].items():
                parquet_bytes = base64.b64decode(serialized_entry['parquet'])
                bytes_io = io.BytesIO(parquet_bytes)
                df = pd.read_parquet(bytes_io, engine='pyarrow')
                deserialized_dfs[key] = {
                    'df': df,
                    'column_metadata': serialized_entry['column_metadata']
                }
            instance.data['dataframes'] = deserialized_dfs
        return instance