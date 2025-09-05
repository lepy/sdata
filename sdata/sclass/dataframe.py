import pandas as pd
import io
import base64
from typing import Any, Dict, Optional
import logging
from sdata.sclass.blob import Blob  # Assuming Blob is in sdata.blob or adjust import
logger = logging.getLogger(__name__)

class DataFrame(Blob):
    def __init__(
        self,
        df: Optional[pd.DataFrame] = pd.DataFrame(),
        column_metadata: Optional[Dict[str, Dict[str, str]]] = None,
        **kwargs: Any
    ) -> None:
        """
        Initialize DataFrame with an optional Pandas DataFrame and optional column metadata.
        If df is provided, serialize it to Parquet bytes and set as Blob content with filetype='parquet'.
        If df is None (e.g., during deserialization), expect content to be set via data.

        :param df: Optional Pandas DataFrame to store.
        :param column_metadata: Optional dict of column metadata, e.g., {colname: {'label': 'Description', 'unit': 'kg'}}.
          If provided, must include all columns in df; colname is the key.
        :param kwargs: Keyword arguments passed to Blob.__init__ (e.g., name, description).
        :raises ValueError: If column_metadata doesn't match df columns.
        """
        if df is not None:
            # Serialize df to Parquet bytes
            bytes_io = io.BytesIO()
            df.to_parquet(bytes_io, engine='pyarrow')
            parquet_bytes = bytes_io.getvalue()

            super().__init__(
                content_type='bytes',
                value=parquet_bytes,
                filetype='parquet',
                **kwargs
            )

            if column_metadata is not None:
                if set(column_metadata.keys()) != set(df.columns):
                    raise ValueError("column_metadata keys must match the DataFrame's columns exactly.")
                for meta in column_metadata.values():
                    if not all(k in meta for k in ['label', 'unit']):
                        raise ValueError("Each column_metadata entry must have 'label' and 'unit' keys.")
            else:
                column_metadata = {col: {'label': '', 'unit': ''} for col in df.columns}

            self.data['column_metadata'] = column_metadata
            logger.debug(f"Created DataFrame '{self.sname}' with {len(df.columns)} columns")
        else:
            super().__init__(**kwargs)
            self.data['column_metadata'] = column_metadata or {}

    @property
    def df(self) -> pd.DataFrame:
        """
        Lazily load and retrieve the DataFrame from Blob content (Parquet bytes).
        Caches the loaded df.
        """
        if 'df_cached' in self.data:
            return self.data['df_cached']

        content_bytes = self.content_bytes  # Lazy load from Blob
        bytes_io = io.BytesIO(content_bytes)
        loaded_df = pd.read_parquet(bytes_io, engine='pyarrow')
        self.data['df_cached'] = loaded_df
        return loaded_df

    @property
    def column_metadata(self) -> Dict[str, Dict[str, str]]:
        """
        Retrieve the column metadata.

        :return: Dict of column metadata {colname: {'label': str, 'unit': str}}.
        """
        return self.data.get('column_metadata', {})

    def update_column_metadata(self, colname: str, label: Optional[str] = None, unit: Optional[str] = None) -> None:
        """
        Update metadata for a specific column.

        :param colname: The column name to update.
        :param label: Optional new label.
        :param unit: Optional new unit.
        :raises KeyError: If colname not in DataFrame columns.
        """
        self.df  # Ensure df is loaded
        if colname not in self.df.columns:
            raise KeyError(f"Column '{colname}' not found in DataFrame.")
        meta = self.column_metadata[colname]
        if label is not None:
            meta['label'] = label
        if unit is not None:
            meta['unit'] = unit
        logger.debug(f"Updated metadata for column '{colname}' in {self.sname}")

    def to_dict(self) -> Dict[str, Any]:
        """
        Extend Blob.to_dict to include column_metadata.
        The content (Parquet bytes) is handled by Blob.
        """
        result = super().to_dict()
        if 'column_metadata' in self.data:
            result['data']['column_metadata'] = self.data['column_metadata']
        return result

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> 'DataFrame':
        """
        Create a DataFrame instance from a dictionary.
        Uses Blob.from_dict and restores column_metadata; df is loaded lazily.
        """
        instance = super().from_dict(d)
        if 'column_metadata' not in instance.data:
            instance.data['column_metadata'] = {}
        return instance

if __name__ == '__main__':
    # Erstelle einen Pandas DataFrame
    import pandas as pd

    df = pd.DataFrame({
        'weight': [10, 20, 30],
        'height': [1.5, 1.6, 1.7]
    })

    # Erstelle eine DataFrame-Instanz mit Metadaten
    column_meta = {
        'weight': {'label': 'Gewicht', 'unit': 'kg'},
        'height': {'label': 'Höhe', 'unit': 'm'}
    }
    sdf = DataFrame(df=df, column_metadata=column_meta, name="MeinDataFrame", description="Beispieldaten")