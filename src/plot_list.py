"""Plot List

Implements view and model class for the list in
the plots dialog.

Written by Sam Hubbard - samlhub@gmail.com
Copyright (C) 2015 Sam Hubbard
"""

from PyQt4.QtGui import *
from PyQt4.QtCore import *

from plot import *


COL_EQUATION = 0
COL_BUTTON = 1


class PlotListTable(QTableView):
    """Table view widget for displaying the loaded plots from a model.

    Attributes:
        deleted_item: Signal emitted when a plot is deleted.
    """
    deleted_item = pyqtSignal()
    
    def __init__(self):
        """Create the table."""
        super(PlotListTable, self).__init__()

        self.setItemDelegate(PlotListDelegate())
        self.itemDelegate().deleted_item.connect(self.clearSelection)
        self.itemDelegate().deleted_item.connect(self.deleted_item)
        self.installEventFilter(self)

        self.setShowGrid(False)
        self.verticalHeader().setVisible(False)
        self.horizontalHeader().setVisible(False)

        self.viewport().setAttribute(Qt.WA_Hover, True)
        self.viewport().setMouseTracking(True)

        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        
    def append(self, plot):
        """Convenience function for adding a plot to the model."""
        self.model().append(plot)
        self.resize_headers()


    def resize_headers(self):
        """The more this is done, the less likely the list will look weird."""
        self.horizontalHeader().setResizeMode(
            COL_EQUATION, QHeaderView.Stretch)
        self.horizontalHeader().setResizeMode(
            COL_BUTTON, QHeaderView.ResizeToContents)
        self.resizeColumnsToContents()

    def mouseReleaseEvent(self, event):
        """Deselects the current plot when clicking in empty space."""
        super(PlotListTable, self).mouseReleaseEvent(event)
        if not self.indexAt(event.pos()).isValid():
            self.clearSelection()

    def eventFilter(self, object, event):
        """Handle events for the table."""
        if event.type() == QEvent.Leave:
            self.itemDelegate().mouseLeft(self.model())
        if event.type() == QEvent.KeyPress:
            if event.key() == Qt.Key_Tab:
                event.ignore()
                return True
            elif event.key() in [Qt.Key_Delete, Qt.Key_Backspace]:
                if self.selectionModel().hasSelection():
                    self.itemDelegate().delete_item(
                        self.model(), self.selectionModel().currentIndex())
        return False


class PlotListModel(QStandardItemModel):
    """Qt model for storing the loaded plots."""
    def __init__(self):
        """Create the model."""
        super(PlotListModel, self).__init__()

    def flags(self, index):
        """Set flags."""
        return Qt.ItemIsSelectable | Qt.ItemIsEnabled

    def append(self, plot):
        """Convenience function for appending a row."""
        self.appendRow([plot, QStandardItem()])

    def __iter__(self):
        """Create and return an iterator for the model."""
        def iterator(self):
            for i in range(self.rowCount()):
                yield self.item(i, 0)
        return iterator(self)


class PlotListDelegate(QStyledItemDelegate):
    """Qt delegate for rendering cells in the plots table.
    
    Attributes:
        hover: The cell currently hovered over by the cursor.
        deleted_item: Signal emitted when a plot is deleted.
    """
    deleted_item = pyqtSignal()

    def __init__(self):
        """Create the delegate."""
        super(PlotListDelegate, self).__init__()
        self.hover = QModelIndex()

    def sizeHint(self, option, index):
        """Take a hint."""
        if index.column() == COL_EQUATION:
            return QSize(0, 24)
        if index.column() == COL_BUTTON:
            return QSize(34, 24)

    def paint(self, painter, option, index):
        """Draw a cell in the table."""
        # Load data from index.
        equation = index.data(ROLE_EQUATION)
        color = index.data(ROLE_COLOR)
        if color: color = QColor(color.rgb())
        button_state = index.data(ROLE_BUTTON_STATE)
        bounds = option.rect
        bounds.adjust(0, 0, 0, -1)

        font = QApplication.font()
        font_metrics = QFontMetrics(font)

        if option.state & QStyle.State_Selected:
            # Highlight the row when selected.
            painter.save()
            painter.setPen(Qt.NoPen)
            if option.state & QStyle.State_Active:
                painter.setBrush(option.palette.highlight())
            else:
                painter.setBrush(option.palette.brush(
                    QPalette.Inactive, QPalette.Highlight))
            painter.drawRect(bounds)
            painter.restore()

        # Draw the delete button.
        if index.column() == COL_BUTTON:
            button = QStyleOptionButton()
            if button_state == STATE_HOVER \
            and option.state & QStyle.State_MouseOver:
                button.state |= QStyle.State_MouseOver
            if button_state == STATE_DOWN:
                button.state |= QStyle.State_Sunken
            button.state |= QStyle.State_Enabled
            button.rect = bounds
            button.text = "\u00D7"
            if option.state & QStyle.State_Selected:
                QApplication.style().drawControl(
                    QStyle.CE_PushButton, button, painter)
            else:
                QApplication.style().drawControl(
                    QStyle.CE_PushButtonLabel, button, painter)

        if index.column() == COL_EQUATION:
            # Draw the coloured block.
            painter.save()
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(color))
            painter.drawRect(bounds.x(), bounds.y(), 12, bounds.height())
            painter.restore()

            # Write out the equation.
            text_bounds = font_metrics.boundingRect(equation)
            text_point = QPointF(
                bounds.x() + 20,
                bounds.y() + (bounds.height() - text_bounds.y()) / 2
            )
            painter.drawText(text_point, equation)

    def editorEvent(self, event, model, option, index):
        """Handles delete button logic."""
        if index.column() == COL_BUTTON:
            if index != self.hover:
                if self.hover.isValid():
                    model.setData(self.hover, STATE_NORMAL, ROLE_BUTTON_STATE)
                if index.isValid():
                    self.hover = index
                else:
                    self.hover = QModelIndex()

            next_state = {
                QEvent.MouseMove: STATE_HOVER,
                QEvent.MouseButtonPress: STATE_DOWN,
                QEvent.MouseButtonDblClick: STATE_DOWN}
            if index.isValid() and event.type() in next_state:
                # If the mouse is moved over the button while pressed, don't
                # revert to the hover state.
                if not (event.type() == QEvent.MouseMove
                   and  index.data(ROLE_BUTTON_STATE) == STATE_DOWN):
                    model.setData(index,
                        next_state[event.type()], ROLE_BUTTON_STATE)

            # If the button is released, delete the index from the model.
            if event.type() == QEvent.MouseButtonRelease \
            and index.data(ROLE_BUTTON_STATE) == STATE_DOWN:
                self.delete_item(model, index)

        return super(PlotListDelegate, self).editorEvent(
            event, model, option, index)

    def delete_item(self, model, index):
        """Deletes a single index from its parent model.

        Also resets the self.hover pointer just in case.
        """
        model.removeRow(index.row())
        self.hover = QModelIndex()
        self.deleted_item.emit()

    def mouseLeft(self, model):
        """Called when the mouse leaves the parent widget's viewport.

        Resets the self.hover pointer.
        """
        if self.hover.isValid():
            model.setData(self.hover, STATE_NORMAL, ROLE_BUTTON_STATE)
            self.hover = QModelIndex()
