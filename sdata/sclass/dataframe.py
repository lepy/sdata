import pandas as pd
import io
import os
import base64
from typing import Any, Dict, Optional, Union
import logging

from sdata.metadata import Metadata, Attribute
# from sdata.sclass.blob import Blob  # Assuming Blob is in sdata.blob or adjust import
from sdata.base import Base

logger = logging.getLogger(__name__)


class DataFrame(Base):
    SDATA_CLS = "sdata.sclass.dataframe.DataFrame"


    def __init__(
            self,
            df: Optional[pd.DataFrame] = pd.DataFrame(),
            column_metadata: Optional[
                Union[Dict[str, Dict[str, str]], Metadata]
            ] = None,
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
        super().__init__(**kwargs)
        self._df = None
        self._column_metadata = Metadata()

        if column_metadata is not None and isinstance(column_metadata, dict):
            self._column_metadata = Metadata.from_dict(column_metadata)
        elif column_metadata is not None and isinstance(column_metadata, Metadata):
            self._column_metadata = column_metadata.copy()
        elif column_metadata is not None:
            logger.warning("column_metadata not supported")
            self._column_metadata = Metadata(name="column_metadata")
        else:
            self._column_metadata = Metadata(name="column_metadata")

        self._df = pd.DataFrame()
        if df is not None:
            self.df = df

    @property
    def cmd(self):
        return self._column_metadata

    @property
    def cmdf(self):
        return self._column_metadata.to_dataframe()

    def _get_df(self):
        return self._df

    def _set_df(self, df):
        if isinstance(df, pd.DataFrame):
            self._df = df
            if self._df.index.name is None:
                self._df.index.name = "index"
            for col in df.columns:
                dtype = df[col].dtype
                self._column_metadata.add(name=col, value=dtype.name)

    df = property(fget=_get_df, fset=_set_df, doc="df object(pandas.DataFrame)")

    @property
    def column_metadata(self) -> Metadata:
        """
        Retrieve the column metadata.

        :return: Dict of column metadata {colname: {'label': str, 'unit': str}}.
        """
        return self._column_metadata

    def to_dict(self) -> Dict[str, Any]:
        """
        Extend Blob.to_dict to include column_metadata.
        The content (Parquet bytes) is handled by Blob.
        """
        result = super().to_dict()
        bytes_io = io.BytesIO()
        self.df.to_parquet(bytes_io, engine='pyarrow')
        parquet_bytes = bytes_io.getvalue()
        result['data']['parquet_bytes'] = base64.b64encode(parquet_bytes).decode("ascii")
        result['data']['column_metadata'] = self.column_metadata.to_dict()
        return result

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> 'DataFrame':
        """
        Create a DataFrame instance from a dictionary.
        Uses Blob.from_dict and restores column_metadata; df is loaded lazily.
        """
        # instance = super().from_dict(d)
        metadata = Metadata.from_dict(d.get("metadata", {}))
        column_metadata_dict = d['data'].get('column_metadata', {})
        column_metadata = Metadata.from_dict(column_metadata_dict)

        instance = cls()
        instance.metadata = metadata
        instance._column_metadata = column_metadata

        parquet_str = d['data'].get('parquet_bytes', '')
        parquet_bytes = base64.b64decode(parquet_str.encode("ascii"))
        instance.df = pd.read_parquet(io.BytesIO(parquet_bytes), engine='pyarrow')
        return instance

    def to_dataframe(self):
        """Export the DataFrame with additional metadata and description.

        Returns:
            pandas.DataFrame: A copy of the DataFrame with added attributes.
        """
        df = self.df.copy()
        df.attrs["!sdata"] = {
            "metadata": self.metadata.to_dict(),
            "description": self.description
        }
        return df

    def to_parquet(self, path=None, filename=None, **kwargs):
        """
        Serialize this sdata.DataFrame to Parquet format, embedding metadata.

        This method will copy the internal pandas DataFrame, attach SData metadata
        (dataset‐level metadata, per‐column metadata, and description) to `df.attrs`,
        and then write the result as a Parquet file. If no output path is given,
        it will return the Parquet bytes buffer.

        Args:
            path (str, optional): Directory where the Parquet file will be saved.
                If provided (and `filename` is None), a file named
                `<sname>.spq` is created under this directory.
            filename (str, optional): Exact filename (without full path)
                for the output Parquet file. Defaults is `<sname>.spq`.
            **kwargs: Additional keyword arguments passed to `pandas.DataFrame.to_parquet`,
                e.g.:
                - engine (str): Parquet engine, defaults to "pyarrow".
                - compression (str): Compression codec, defaults to "zstd".

        Returns:
            str or bytes:
                - If `path` (or `filename`) is provided, returns the full file path (str)
                  where the Parquet file was written.
                - Otherwise, returns the in‐memory Parquet representation as bytes.

        Example:
            # Save to disk under /data/output/<sname>.spq with default naming:
            out_fp = sdf.to_parquet(path="/data/output")
            print("Saved to:", out_fp)

            # Get in‐memory Parquet bytes (no file on disk):
            parquet_bytes = sdf.to_parquet()
        """
        engine = kwargs.get("engine", "pyarrow")
        compression = kwargs.get("compression", "zstd")

        df = self.df.copy()
        df.attrs["_sdata"] = {"metadata": self.metadata.to_dict(),
                              "column_metadata": self.column_metadata.to_dict(),
                              "description": self.description}

        if filename is None and path is not None:
            filename = self.sname + ".spq"
            filepath = os.path.join(path, filename)
            df.to_parquet(filepath, engine=engine, compression=compression)
            logger.info(f"DataFrame Parquet saved to {filepath}")
            return filepath
        else:
            return df.to_parquet(engine=engine, compression=compression)

    @classmethod
    def from_parquet_bytes(cls, parquet_bytes, **kwargs):
        """load data from parquet file

        :param filepath:
        :return: Data object
        """
        engine = kwargs.get("engine", "pyarrow")
        buffer = io.BytesIO(parquet_bytes)
        df = pd.read_parquet(buffer, engine=engine)
        tt = cls()
        tt.df = df

        attrs = df.attrs.get("_sdata")
        try:
            tt.metadata = tt.metadata.from_dict(attrs["metadata"])
        except:
            logger.warning(f"ignore metadata")

        try:
            tt._column_metadata = tt.metadata.from_dict(attrs["column_metadata"])
        except:
            logger.warning(f"ignore column_metadata")

        try:
            tt.description = attrs.get("description")
        except:
            logger.warning(f"ignore description")

        return tt

    @classmethod
    def from_parquet(cls, filepath):
        """load data from parquet file

        :param filepath:
        :return: Data object
        """
        try:
            if os.path.exists(filepath):
                df = pd.read_parquet(filepath)
                tt = cls(name=filepath)
                tt.df = df
                logger.info(f"{tt}")
                attrs = df.attrs.get("_sdata")
                try:
                    tt.metadata = tt.metadata.from_dict(attrs["metadata"])
                except:
                    logger.warning(f"ignore metadata {filepath}")

                try:
                    tt._column_metadata = tt.metadata.from_dict(attrs["column_metadata"])
                except:
                    logger.warning(f"ignore column_metadata")

                try:
                    tt.description = attrs.get("description")
                except:
                    logger.warning(f"ignore description {filepath}")
                if attrs is not None:
                    tt.df.attrs.pop("_sdata")

                return tt
            else:
                raise Exception(f"no DataFrame parquet file {filepath}")

        except Exception as exp:
            raise


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
