# encoding: utf-8

"""
.. codeauthor:: Tsuyoshi Hombashi <tsuyoshi.hombashi@gmail.com>
"""

from __future__ import absolute_import

import abc

import six


@six.add_metaclass(abc.ABCMeta)
class TableWriterInterface(object):
    """
    Interface class for writing a table.
    """

    @abc.abstractproperty
    def format_name(self):  # pragma: no cover
        """
        :return: Format name for the writer.
        :rtype: str
        """

        pass

    @abc.abstractproperty
    def support_split_write(self):  # pragma: no cover
        """
        :return:
            |True| if the writer supported iterative table writing (``write_table_iter`` method).
        :rtype: bool
        """

        pass

    @abc.abstractmethod
    def write_table(self):  # pragma: no cover
        """
        |write_table|.
        """

        pass

    def dump(self, output, close_after_write):  # pragma: no cover
        raise NotImplementedError("{} writer did not support dump method".format(self.format_name))

    def dumps(self):  # pragma: no cover
        raise NotImplementedError("{} writer did not support dumps method".format(self.format_name))

    def write_table_iter(self):  # pragma: no cover
        """
        Write a table with iteration. "Iteration" means that divide the table
        writing into multiple processes.
        This method is useful, especially for large data.
        The following are premises to execute this method:

        - set iterator to the |value_matrix|
        - set the number of iterations to the |iteration_length| attribute

        Call back function (Optional):
        Callback function is called when for each of the iteration of writing
        a table is completed. To set call back function,
        set a callback function to the |write_callback| attribute.

        :raises pytablewriter.NotSupportedError:
            If the class does not support this method.

        .. note::
            Following classes do not support this method:
            |HtmlTableWriter|, |RstGridTableWriter|, |RstSimpleTableWriter|.
            ``support_split_write`` attribute return |True| if the class
            is supporting this method.
        """

        self._write_table_iter()

    @abc.abstractmethod
    def _write_table_iter(self):  # pragma: no cover
        pass

    @abc.abstractmethod
    def close(self):  # pragma: no cover
        pass

    @abc.abstractmethod
    def _write_value_row_separator(self):  # pragma: no cover
        pass
