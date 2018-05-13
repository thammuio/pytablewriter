# encoding: utf-8

"""
.. codeauthor:: Tsuyoshi Hombashi <tsuyoshi.hombashi@gmail.com>
"""

from __future__ import absolute_import, unicode_literals

import abc
import re
import sys

import msgfy
import typepy
from six.moves import zip
from tabledata import convert_idx_to_alphabet
from typepy import Typecode

from .._error import (
    EmptyHeaderError, EmptyTableDataError, EmptyTableNameError, EmptyValueError, NotSupportedError)
from .._logger import WriterLogger
from ._interface import TableWriterInterface


class AbstractTableWriter(TableWriterInterface):
    """
    An abstract base class of table writer classes.

    .. py:attribute:: stream

        Stream to write tables.
        You can use arbitrary stream which supported ``write`` method
        such as ``sys.stdout``, file stream, ``StringIO``, and so forth.
        Defaults to ``sys.stdout``.

    .. py:attribute:: is_write_header

        Write headers of a table if the value is |True|.

    .. py:attribute:: is_padding

        Padding for each item in the table if the value is |True|.

    .. py:attribute:: iteration_length

        The number of iterations to write a table.
        This value used in :py:meth:`.write_table_iter` method.
        (defaults to ``-1`` which means number of iterations is indefinite)

    .. py:attribute:: write_callback

        The value expected to a function.
        The function called when for each of the iteration of writing a table
        completed. (defaults to |None|)
        Example, callback function definition is as follows:

        .. code:: python

            def callback_example(iter_count, iter_length):
                print("{:d}/{:d}".format(iter_count, iter_length))

        Arguments that passed to the callback is:

        - first argument: current iteration number (start from ``1``)
        - second argument: a total number of iteration
    """

    __RE_LINE_BREAK = re.compile("[\0\t\r\n]+")

    @property
    def is_formatting_float(self):
        return self._dp_extractor.is_formatting_float

    @is_formatting_float.setter
    def is_formatting_float(self, value):
        if self._dp_extractor.is_formatting_float == value:
            return

        self._dp_extractor.is_formatting_float = value
        self.__clear_preprocess()

    @property
    def table_name(self):
        """
        Name of the table.
        """

        return self._table_name

    @table_name.setter
    def table_name(self, value):
        self._table_name = value

    @property
    def header_list(self):
        """
        List of table header to write.
        """

        return self._dp_extractor.header_list

    @header_list.setter
    def header_list(self, value):
        self._dp_extractor.header_list = value

    @property
    def value_matrix(self):
        """
        Tabular data to write.
        """

        return self.__value_matrix_org

    @value_matrix.setter
    def value_matrix(self, value_matrix):
        self.__set_value_matrix(value_matrix)
        self.__clear_preprocess()

    @property
    def tabledata(self):
        """
        :return: Table data.
        :rtype: tabledata.TableData
        """

        from tabledata import TableData

        return TableData(self.table_name, self.header_list, self.value_matrix)

    @property
    def type_hint_list(self):
        """
        List of type hints for each column of the tabular data.
        Acceptable values are as follows:

            - |None| (automatically detect column type from values in the column)
            - :py:class:`pytablewriter.Bool`
            - :py:class:`pytablewriter.DateTime`
            - :py:class:`pytablewriter.Dictionary`
            - :py:class:`pytablewriter.Infinity`
            - :py:class:`pytablewriter.Integer`
            - :py:class:`pytablewriter.List`
            - :py:class:`pytablewriter.Nan`
            - :py:class:`pytablewriter.NoneType`
            - :py:class:`pytablewriter.NullString`
            - :py:class:`pytablewriter.RealNumber`
            - :py:class:`pytablewriter.String`

        A writer converts data for each column using type-hint
        information before writing tables when you call ``write_xxx`` methods.
        If a type-hint value is not |None|, the writer tries to
        convert data for each data in a column to type-hint class.
        If the type-hint value is |None| or failed to convert data,
        the writer automatically detect column data type from
        the column data.

        If ``type_hint_list`` is |None|, the writer detects data types for all
        of the columns automatically and writes a table by using detected
        column types.
        Defaults to |None|.

        :Examples:
            :ref:`example-type-hint-js`
        """

        return self._dp_extractor.column_type_hint_list

    @type_hint_list.setter
    def type_hint_list(self, value):
        self.__set_type_hint_list(value)
        self.__clear_preprocess()

    @property
    def _quoting_flags(self):
        return self._dp_extractor.quoting_flags

    @_quoting_flags.setter
    def _quoting_flags(self, value):
        self._dp_extractor.quoting_flags = value
        self.__clear_preprocess()

    @abc.abstractmethod
    def _write_table(self):
        pass

    def __init__(self):
        from dataproperty import (Align, DataPropertyExtractor, MatrixFormatting)

        self._logger = WriterLogger(self)

        self.stream = sys.stdout
        self._table_name = None
        self.value_matrix = None

        self.is_write_header = True
        self.is_write_header_separator_row = True
        self.is_write_value_separator_row = False
        self.is_write_opening_row = False
        self.is_write_closing_row = False

        self._use_default_header = False

        self._dp_extractor = DataPropertyExtractor()
        self._dp_extractor.min_column_width = 1
        self._dp_extractor.strip_str_header = '"'
        self._dp_extractor.strip_str_value = '"'
        self._dp_extractor.type_value_mapping[Typecode.NONE] = ""
        self._dp_extractor.matrix_formatting = MatrixFormatting.HEADER_ALIGNED

        self.is_formatting_float = True
        self.is_padding = True

        self.header_list = None
        self.type_hint_list = None
        self._quoting_flags = {
            Typecode.BOOL: False,
            Typecode.DATETIME: True,
            Typecode.DICTIONARY: False,
            Typecode.INFINITY: False,
            Typecode.INTEGER: False,
            Typecode.IP_ADDRESS: True,
            Typecode.LIST: False,
            Typecode.NAN: False,
            Typecode.NONE: False,
            Typecode.NULL_STRING: True,
            Typecode.REAL_NUMBER: False,
            Typecode.STRING: True,
        }

        self._is_require_table_name = False
        self._is_require_header = False
        self._is_remove_line_break = False

        self.iteration_length = -1
        self.write_callback = lambda _iter_count, _iter_length: None  # NOP
        self.__iter_count = None

        self.__align_char_mapping = {
            Align.AUTO: "<",
            Align.LEFT: "<",
            Align.RIGHT: ">",
            Align.CENTER: "^",
        }

        self.__clear_preprocess()

    def _repr_html_(self):
        import six
        from ._html import HtmlTableWriter

        writer = HtmlTableWriter()
        writer.table_name = self.table_name
        writer.header_list = self.header_list
        writer.value_matrix = self.value_matrix
        writer.stream = six.StringIO()
        writer.write_table()

        return writer.stream.getvalue()

    def close(self):
        """
        Close the current |stream|.
        """

        try:
            if self.stream.name in ["<stdin>", "<stdout>", "<stderr>"]:
                return
        except AttributeError:
            pass

        try:
            self.stream.close()
        except AttributeError:
            self._logger.logger.warn("the stream has no close method implementation")
        finally:
            self.stream = None

    def from_tabledata(self, value, is_overwrite_table_name=True):
        """
        Set tabular attributes to the writer from |TableData|.
        Following attributes are configured:

        - :py:attr:`~.table_name`.
        - :py:attr:`~.header_list`.
        - :py:attr:`~.value_matrix`.

        |TableData| can be created from various data formats by
        ``pytablereader``. More detailed information can be found in
        http://pytablereader.readthedocs.io/en/latest/

        :param tabledata.TableData value: Input table data.
        """

        self.__clear_preprocess()

        if is_overwrite_table_name:
            self.table_name = value.table_name

        self.header_list = value.header_list
        self._table_value_dp_matrix = value.value_dp_matrix
        self._column_dp_list = self._dp_extractor.to_column_dp_list(
            self._table_value_dp_matrix, self._column_dp_list)
        self.__set_type_hint_list([col_dp.type_class for col_dp in self._column_dp_list])

        self._is_complete_table_dp_preprocess = True

    def from_csv(self, csv_source):
        """
        Set tabular attributes to the writer from a character-separated values (CSV) data source.
        Following attributes are set to the writer by the method:

        - :py:attr:`~.header_list`.
        - :py:attr:`~.value_matrix`.

        :py:attr:`~.table_name` also be set if the CSV data source is a file.
        In that case, :py:attr:`~.table_name` is as same as the filename.

        :param str csv_source:
            Input CSV data source either can be designated CSV text or
            CSV file path.

        :Examples:
            :ref:`example-from-csv`

        :Dependency Packages:
            - `pytablereader <https://github.com/thombashi/pytablereader>`__
        """

        import pytablereader as ptr

        loader = ptr.CsvTableTextLoader(csv_source, quoting_flags=self._quoting_flags)
        try:
            for table_data in loader.load():
                self.from_tabledata(table_data, is_overwrite_table_name=False)
            return
        except ptr.InvalidDataError:
            pass

        loader = ptr.CsvTableFileLoader(csv_source, quoting_flags=self._quoting_flags)
        for table_data in loader.load():
            self.from_tabledata(table_data)

    def from_dataframe(self, dataframe):
        """
        Set tabular attributes to the writer from :py:class:`pandas.DataFrame`.
        Following attributes are set to the writer by the method:

        - :py:attr:`~.header_list`.
        - :py:attr:`~.value_matrix`.
        - :py:attr:`~.type_hint_list`.

        :param pandas.DataFrame dataframe: Input dataframe.

        :Example:
            :ref:`example-from-pandas-dataframe`
        """

        self.header_list = list(dataframe.columns.values)
        self.value_matrix = dataframe.values.tolist()
        self.type_hint_list = [
            self.__get_typehint_from_dtype(dtype) for dtype in dataframe.dtypes
        ]

    def write_table(self):
        """
        |write_table|.
        """

        self._logger.logging_start_write()
        self._verify_property()
        self._write_table()
        self._logger.logging_complete_write()

    def _write_table_iter(self):
        if not self.support_split_write:
            raise NotSupportedError(
                "the class not supported the write_table_iter method")

        self._verify_table_name()
        self._verify_stream()

        if all([typepy.is_empty_sequence(self.header_list),
                typepy.is_empty_sequence(self.value_matrix)]):
            raise EmptyTableDataError()

        self._verify_header()

        self._logger.logging_start_write([
            "iteration-length={:d}".format(self.iteration_length)
        ])

        stash_is_write_header = self.is_write_header
        stach_is_write_opening_row = self.is_write_opening_row
        stash_is_write_closing_row = self.is_write_closing_row

        try:
            self.is_write_closing_row = False
            self.__iter_count = 1

            for work_matrix in self.value_matrix:
                is_final_iter = all([
                    self.iteration_length > 0,
                    self.__iter_count >= self.iteration_length
                ])

                if is_final_iter:
                    self.is_write_closing_row = True

                self.__set_value_matrix(work_matrix)
                self.__clear_preprocess_status()

                self._write_table()

                if not is_final_iter:
                    self._write_value_row_separator()

                self.is_write_opening_row = False
                self.is_write_header = False

                self.write_callback(self.__iter_count, self.iteration_length)

                # update typehint for the next iteration
                """
                if self.type_hint_list is None:
                    self.__set_type_hint_list([
                        column_dp.type_class for column_dp in self._column_dp_list
                    ])
                """

                if is_final_iter:
                    break

                self.__iter_count += 1
        finally:
            self.is_write_header = stash_is_write_header
            self.is_write_opening_row = stach_is_write_opening_row
            self.is_write_closing_row = stash_is_write_closing_row
            self.__iter_count = None

        self._logger.logging_complete_write()

    def _get_padding_len(self, column_dp, value_dp=None):
        if not self.is_padding:
            return 0

        try:
            return value_dp.get_padding_len(column_dp.ascii_char_width)
        except AttributeError:
            return column_dp.ascii_char_width

    def _get_header_item(self, col_dp, value_dp):
        from typepy import String

        format_string = self._get_header_format_string(col_dp, value_dp)
        header = String(value_dp.data).force_convert().strip()

        return format_string.format(self.__remove_line_break(header))

    @staticmethod
    def _get_header_format_string(_col_dp, _value_dp):
        return "{:s}"

    def _get_row_item(self, col_dp, value_dp):
        return self.__get_align_format(col_dp, value_dp).format(
            self.__remove_line_break(col_dp.dp_to_str(value_dp)))

    def _get_align_char(self, align):
        return self.__align_char_mapping[align]

    def __get_align_format(self, col_dp, value_dp):
        if (col_dp.typecode == Typecode.STRING and
                value_dp.typecode in (Typecode.INTEGER, Typecode.REAL_NUMBER)):
            align_char = self._get_align_char(value_dp.align)
        else:
            align_char = self._get_align_char(col_dp.align)
        format_list = ["{:" + align_char]
        col_padding_len = self._get_padding_len(col_dp, value_dp)
        if col_padding_len > 0:
            format_list.append(str(col_padding_len))
        format_list.append("s}")

        return "".join(format_list)

    @staticmethod
    def __get_typehint_from_dtype(col_dtype):
        col_dtype = str(col_dtype)

        if re.search("^float", col_dtype):
            return typepy.RealNumber

        if re.search("^int", col_dtype):
            return typepy.Integer

        return None

    def _verify_property(self):
        self._verify_table_name()
        self._verify_stream()

        if all([
                typepy.is_empty_sequence(self.header_list),
                typepy.is_empty_sequence(self.value_matrix),
                typepy.is_empty_sequence(self._table_value_dp_matrix),
        ]):
            raise EmptyTableDataError()

        self._verify_header()
        try:
            self._verify_value_matrix()
        except EmptyValueError:
            pass

    def __set_value_matrix(self, value_matrix):
        self.__value_matrix_org = value_matrix

    def __set_type_hint_list(self, type_hint_list):
        self._dp_extractor.column_type_hint_list = type_hint_list

    def _verify_table_name(self):
        if all([self._is_require_table_name,
                typepy.is_null_string(self.table_name)]):
            raise EmptyTableNameError(
                "table_name must be a string, with at least one or more character.")

    def _verify_stream(self):
        if self.stream is None:
            raise IOError("null output stream")

    def _verify_header(self):
        if self._is_require_header and not self._use_default_header:
            self._validate_empty_header()

    def _validate_empty_header(self):
        """
        :raises pytablewriter.EmptyHeaderError: If the |header_list| is empty.
        """

        if typepy.is_empty_sequence(self.header_list):
            raise EmptyHeaderError(
                "header_list expected to have one or more header names")

    def _verify_value_matrix(self):
        if typepy.is_empty_sequence(self.value_matrix):
            raise EmptyValueError()

    def _preprocess_table_dp(self):
        if self._is_complete_table_dp_preprocess:
            return

        self._logger.logger.debug("_preprocess_table_dp")

        if typepy.is_empty_sequence(self.header_list) and self._use_default_header:
            self.header_list = [
                convert_idx_to_alphabet(col_idx)
                for col_idx in range(len(self.__value_matrix_org[0]))
            ]

        try:
            self._table_value_dp_matrix = self._dp_extractor.to_dp_matrix(self.__value_matrix_org)
        except TypeError as e:
            self._logger.logger.debug(msgfy.to_error_message(e))
            self._table_value_dp_matrix = []

        self._column_dp_list = self._dp_extractor.to_column_dp_list(
            self._table_value_dp_matrix, self._column_dp_list)

        self._is_complete_table_dp_preprocess = True

    def _preprocess_table_property(self):
        if self._is_complete_table_property_preprocess:
            return

        self._logger.logger.debug("_preprocess_table_property")

        if self.__iter_count == 1:
            import math

            for column_dp in self._column_dp_list:
                column_dp.extend_width(int(math.ceil(column_dp.ascii_char_width * 0.25)))

        self._is_complete_table_property_preprocess = True

    def _preprocess_header(self):
        if self._is_complete_header_preprocess:
            return

        self._logger.logger.debug("_preprocess_header")

        self._table_header_list = [
            self._get_header_item(col_dp, header_dp)
            for col_dp, header_dp in
            zip(self._column_dp_list, self._dp_extractor.to_header_dp_list())
        ]

        self._is_complete_header_preprocess = True

    def _preprocess_value_matrix(self):
        if self._is_complete_value_matrix_preprocess:
            return

        self._logger.logger.debug("_preprocess_value_matrix: value-rows={}".format(
            len(self._table_value_dp_matrix)))

        self._table_value_matrix = [
            [
                self._get_row_item(col_dp, value_dp)
                for col_dp, value_dp in zip(self._column_dp_list, value_dp_list)
            ]
            for value_dp_list in self._table_value_dp_matrix
        ]

        self._is_complete_value_matrix_preprocess = True

    def _preprocess(self):
        self._preprocess_table_dp()
        self._preprocess_table_property()
        self._preprocess_header()
        self._preprocess_value_matrix()

    def __clear_preprocess_status(self):
        try:
            if any([
                self._is_complete_table_dp_preprocess,
                self._is_complete_table_property_preprocess,
                self._is_complete_header_preprocess,
                self._is_complete_value_matrix_preprocess,
            ]):
                self._logger.logger.debug("__clear_preprocess_status")
        except AttributeError:
            pass

        self._is_complete_table_dp_preprocess = False
        self._is_complete_table_property_preprocess = False
        self._is_complete_header_preprocess = False
        self._is_complete_value_matrix_preprocess = False

    def __clear_preprocess_data(self):
        try:
            if any([
                self._column_dp_list,
                self._table_header_list,
                self._table_value_matrix,
                self._table_value_dp_matrix,
            ]):
                self._logger.logger.debug("__clear_preprocess_data")
        except AttributeError:
            pass

        self._column_dp_list = []
        self._table_header_list = []
        self._table_value_matrix = []
        self._table_value_dp_matrix = []

    def __clear_preprocess(self):
        self.__clear_preprocess_status()
        self.__clear_preprocess_data()

    def __remove_line_break(self, text):
        if not self._is_remove_line_break:
            return text

        return self.__RE_LINE_BREAK.sub(" ", text)
