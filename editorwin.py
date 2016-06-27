from PyQt4 import QtCore, QtGui, uic
import icons
from collections import namedtuple

from const import *
from classes import *
from utils import *

TPatch = namedtuple('TPatch', 'label patch input')
TPatch.__new__.__defaults__ = (None, ) * len(TPatch._fields)
TPatch.__new__.__defaults__ = (None, )

class OutputWidget(QtGui.QWidget):
    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)
        uic.loadUi('output_widget.ui', self)
        self.main = self.parent()

class EditorWin(QtGui.QMainWindow):
    labelChanged = QtCore.pyqtSignal(object, object)
    widgetSaved = QtCore.pyqtSignal(int)

    def __init__(self, parent=None, mode='control'):
        QtGui.QMainWindow.__init__(self, parent)
        self.main = self.parent()
        self.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.conf_dict = self.main.conf_dict
        self.map_dict = self.main.map_dict
        uic.loadUi('patch.ui', self)
        self.statusbar_create()
        self.patch_edit.textChanged.connect(self.patch_update)
        self.patch = ''
        self.patch_edit.valid = False
        self.main.widgetChanged.connect(self.widget_change)
        self.patch_edit.focusInEvent = self.patch_edit_focusIn
        self.patch_edit.focusOutEvent = self.patch_edit_focusOut
        self.enable_chk.toggled.connect(self.enable_set)
        self.led_reset_btn.clicked.connect(self.led_reset)
        self.main.outputChanged.connect(self.output_update)
        self.dest_combo.currentIndexChanged.connect(self.dest_update)
        self.led_combo.currentIndexChanged.connect(self.led_combo_update)
        self.text_edit.textEdited.connect(self.text_update)
        self.led_action_combo.lineEdit().textEdited.connect(self.led_action_update)
        self.restore_btn.clicked.connect(self.widget_restore)
        self.tool_group.setEnabled = self.tool_group_setEnabled
        self.toggle_chk.toggled.connect(self.toggle_set)
        self.toggle_listview.wheelEvent = self.toggle_chk_wheelEvent
        self.toggle_add_btn.clicked.connect(self.toggle_value_add)
        self.toggle_remove_btn.clicked.connect(self.toggle_value_remove)
        self.toggle_listview.closeEditor = self.toggle_validate
        self.convert_chk.toggled.connect(self.convert_enable)
        self.chan_reset_btn.clicked.connect(self.chan_reset)

        self.convert_ctrl_radio.id = ToCtrl
        self.convert_note_radio.id = ToNote
        self.current_widget = None
        self.output_update()
        self.models_setup()
        self.base_group.setEnabled(False)
        self.patch_group.setEnabled(False)
        self.patch_templates_menu_create()
        self.patch_toolbtn.setMenu(self.patch_templates)
        self.toggle_set(False)

    def toggle_chk_wheelEvent(self, event):
        if event.orientation() == QtCore.Qt.Vertical:
            hbar = self.toggle_listview.horizontalScrollBar()
            if event.delta() < 1:
                hbar.setValue(hbar.value()+hbar.pageStep())
            else:
                hbar.setValue(hbar.value()-hbar.pageStep())

    def toggle_validate(self, delegate, hint):
        QtGui.QListView.closeEditor(self.toggle_listview, delegate, hint)
        index = self.toggle_listview.currentIndex().row()
        item = self.toggle_listview.model().item(index, 0)
        value = item.text()
        try:
            int_value = int(value)
            if int_value < 0:
                item.setText('0')
            elif int_value > 127:
                item.setText('127')
        except:
            item.setText('127')

    def toggle_set(self, value):
        self.toggle_listview.setEnabled(value)
        self.toggle_remove_btn.setEnabled(value)
        self.toggle_add_btn.setEnabled(value)
        if not self.current_widget:
            return
        if value and not (self.current_widget.get('toggle') or self.current_widget.get('toggle_values') or self.current_widget.get('toggle_model')):
            toggle_model = QtGui.QStandardItemModel()
            for i in [0, 127]:
                item = QtGui.QStandardItem(str(i))
                item.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsDragEnabled)
                toggle_model.appendRow(item)
                self.current_widget['toggle_values'] = (0, 127)
                self.current_widget['toggle_model'] = toggle_model
            self.toggle_listview.setModel(toggle_model)
        self.current_widget['toggle'] = value
        action = self.current_widget['widget'].toggle_action
        if action:
            #NOTE: I suppose that this might change in future version of Qt, since it could send a signal. Keep an eye
            action.setChecked(value)

    def toggle_value_add(self):
        if self.toggle_listview.model().rowCount() > 8:
            return
        item = QtGui.QStandardItem('127')
        item.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsDragEnabled)
        self.toggle_listview.model().appendRow(item)
        self.toggle_range_check()

    def toggle_value_remove(self):
        if self.toggle_listview.model().rowCount() <= 2:
            return
        index = self.toggle_listview.currentIndex().row()
        if index < 0:
            index = self.toggle_listview.model().rowCount()-1
        self.toggle_listview.model().takeRow(index)
        self.toggle_range_check()

    def toggle_range_check(self):
        if not self.toggle_listview.model():
            return
        if self.toggle_listview.model().rowCount() >= 8:
            self.toggle_add_btn.setEnabled(False)
        else:
            self.toggle_add_btn.setEnabled(True)
        if self.toggle_listview.model().rowCount() <= 2:
            self.toggle_remove_btn.setEnabled(False)
        else:
            self.toggle_remove_btn.setEnabled(True)

    def convert_enable(self, value):
        for button in self.convert_group.buttons():
            button.setEnabled(value)

    def chan_enable(self, value):
        self.chan_spin.setEnabled(value)


    def closeEvent(self, event):
        if self.current_widget:
            self.widget_save()

    def event(self, event):
        if event.type() == QtCore.QEvent.WindowDeactivate:
            self.widget_save()
        return QtGui.QMainWindow.event(self, event)

    def patch_templates_menu_create(self):
        action_dict = [(
                       'Ctrl value split', (
                            TPatch('2 value filter to 0, 127', 'CtrlValueSplit({(0,63): Ctrl(EVENT_DATA1, 0), (64,127): Ctrl(EVENT_DATA1, 127)})'), 
                            TPatch('3 value filter to 0, 64, 127', 'CtrlValueSplit({(0,42): Ctrl(EVENT_DATA1, 0), (43,84): Ctrl(EVENT_DATA1, 64), (85,127): Ctrl(EVENT_DATA1, 127)})'), 
                            TPatch('4 value filter to 0, 32, 64, 127', 'CtrlValueSplit({(0,31): Ctrl(EVENT_DATA1, 0), (32,63): Ctrl(EVENT_DATA1, 42), (64,95): Ctrl(EVENT_DATA1, 84), (96, 127): Ctrl(EVENT_DATA1, 127)})'), 
                            TPatch('6 value filter to 0, 26, 51, 77, 102, 127', 'CtrlValueSplit({(0,21): Ctrl(EVENT_DATA1, 0), (22,42): Ctrl(EVENT_DATA1, 26), (43,63): Ctrl(EVENT_DATA1, 51), (64, 85): Ctrl(EVENT_DATA1, 77), (86, 106): Ctrl(EVENT_DATA1, 102), (107, 127): Ctrl(EVENT_DATA1, 127)})')
                       )), (
                       'Ctrl Remap', (
                            TPatch('Remap to Ctrl...', 'Ctrl({}, EVENT_VALUE)', ((int, 127, 'Set Ctrl number to remap to'), )), 
                       )), 
#                       TPatch('Test',  'oirgour'), 
                      ]
        self.patch_templates = QtGui.QMenu()
#        print action_dict.items()
        for item in action_dict:
            if isinstance(item, TPatch):
                action = QtGui.QAction(item.label, self)
                action.patch = item.patch
                if item.input:
                    action.input = item.input
                else:
                    action.input = None
                action.triggered.connect(self.patch_template_set)
                self.patch_templates.addAction(action)
            else:
                label, patch_list = item
                submenu = self.patch_templates.addMenu(label)
                for tpatch in patch_list:
                    action = QtGui.QAction(tpatch.label, self)
                    action.patch = tpatch.patch
                    if tpatch.input:
                        action.input = tpatch.input
                    else:
                        action.input = None
                    action.triggered.connect(self.patch_template_set)
                    submenu.addAction(action)

    def patch_template_set(self):
        action = self.sender()
        patch = action.patch
        if action.input:
            for req in action.input:
                if req[0] == int:
                    value, res = QtGui.QInputDialog.getInt(self, action.text(), req[-1], min=0, max=req[1])
                    if not res:
                        return
                    patch = patch.format(value)
                
        if self.patch_edit.toPlainText().toLatin1() == 'Pass()':
            self.patch_edit.setPlainText(patch)
            return
        doc = self.patch_edit.document()
        excursor = self.patch_edit.textCursor()
        cursor = QtGui.QTextCursor(doc)
        cursor.setPosition(excursor.position())
        cursor.insertText(patch)

    def widget_restore(self):
        self.clear_fields(False)
        self.labelChanged.emit(self.current_widget['widget'], True)

    def clear_fields(self, disable=True):
        self.dest_combo.setCurrentIndex(0)
        self.text_edit.setText('')
        if self.current_widget:
            widget = self.current_widget['widget']
            self.led_combo.setCurrentIndex(widget.siblingLed+1 if widget.siblingLed else 0)
        else:
            self.led_combo.setCurrentIndex(0)
        self.led_base_combo.setCurrentIndex(0)
        self.led_base_combo.setModelColumn(0)
        self.led_action_combo.setCurrentIndex(-1)
#        self.led_action_combo.setModelColumn(0)
        self.patch_edit.setPlainText('')
        if disable:
            self.enable_chk.setChecked(False)

    def output_update(self):
        prev_index = self.dest_combo.currentIndex()
        self.dest_combo.blockSignals(True)
        self.output_model = QtGui.QStandardItemModel(self.dest_combo)
        self.dest_combo.setModel(self.output_model)
        for i in range(self.main.output_model.rowCount()):
            item = self.main.output_model.item(i).clone()
            item.setText('{}: {}{}'.format(i+1, item.text(), ' (default)' if i == 0 else ''))
            font = item.font()
            font.setBold(False)
            item.setFont(font)
            self.output_model.appendRow(item)
        if self.current_widget and prev_index > 0:
            if prev_index >= self.output_model.rowCount():
                prev_index = self.output_model.rowCount()-1
                self.dest_combo.blockSignals(False)
            self.dest_combo.setCurrentIndex(prev_index)
        self.dest_combo.blockSignals(False)

    def models_setup(self):
        def pixmap(red=0, green=0):
            pixmap = QtGui.QPixmap(8, 8)
            color = QtGui.QColor()
            color.setRgb(red, green, 0)
            pixmap.fill(color)
            return pixmap
        def create_table():
            table = QtGui.QTableView(self)
            table.setShowGrid(False)
            table.verticalHeader().hide()
            table.horizontalHeader().hide()
            table.setSelectionMode(QtGui.QAbstractItemView.SingleSelection)
            table.setSelectionBehavior(QtGui.QAbstractItemView.SelectItems)
            return table

        #Led list
        self.ledlist_model = QtGui.QStandardItemModel(self.led_combo)
        self.led_combo.setModel(self.ledlist_model)
        item = QtGui.QStandardItem('Disabled')
        item.led = None
        item.ledSet = None
        item.ledTrigger = None
        self.ledlist_model.appendRow(item)
        for widget in self.main.widget_order:
            if widget.siblingLed == None:
                continue
            item = QtGui.QStandardItem(widget.readable)
            item.led = widget.siblingLed
            item.ledSet = widget.ledSet
            item.ledTrigger = widget.ledTrigger
            self.ledlist_model.appendRow(item)

        #LED base color combo
        self.colormap_full_pixmap = {(r, g):pixmap(r*85, g*85) for r in range(4) for g in range(4)}
        self.colormap_full_model = QtGui.QStandardItemModel()
        self.led_base_combo.setModel(self.colormap_full_model)
        self.color_table = create_table()
        self.color_table.selectionChanged = self.color_column_check
        self.led_base_combo.setView(self.color_table)
        for row in range(4):
            row_list = []
            for col in range(4):
                item = QtGui.QStandardItem('0x{:02x}'.format(row+col*16))
                item.setIcon(QtGui.QIcon(self.colormap_full_pixmap[row, col]))
#                if row == 0 and col == 3:
#                    font = item.font()
#                    font.setBold(True)
#                    item.setFont(font)
                row_list.append(item)
            self.colormap_full_model.appendRow(row_list)
            self.color_table.resizeColumnToContents(row)
        self.color_table.setMinimumWidth(sum([self.color_table.columnWidth(c) for c in range(self.colormap_full_model.columnCount())]))

        self.colormap_dev_pixmap = [pixmap(r*42, r*38) for r in range(7)]
        self.colormap_dev_model = QtGui.QStandardItemModel()
        for l in range(7):
            led_value = dev_scale[l]
            item = QtGui.QStandardItem('0x{:02x}'.format(led_value))
            item.setIcon(QtGui.QIcon(self.colormap_dev_pixmap[l]))
            self.colormap_dev_model.appendRow(item)
        self.led_base_combo.setSizeAdjustPolicy(self.led_base_combo.AdjustToContents)

        self.colormap_dir_pixmap = [pixmap(r*51) for r in range(6)]
        self.colormap_dir_model = QtGui.QStandardItemModel()
        for l in range(6):
            led_value = dir_scale[l]
            item = QtGui.QStandardItem('0x{:02x}'.format(led_value))
            item.setIcon(QtGui.QIcon(self.colormap_dir_pixmap[l]))
            self.colormap_dir_model.appendRow(item)

        #LED action combo
        self.action_table = create_table()
        self.action_table.selectionChanged = self.action_column_check
        self.led_action_combo.setView(self.action_table)
        self.action_full_model = QtGui.QStandardItemModel()
        self.led_action_combo.setModel(self.action_full_model)
        pass_item = QtGui.QStandardItem('Pass')
        disc_item = QtGui.QStandardItem('Ignore')
        toggle_item = QtGui.QStandardItem('Toggle')
        self.action_full_model.appendRow([pass_item, disc_item, toggle_item])
        self.action_table.setSpan(0, 2, 1, 2)
        self.action_table.resizeRowToContents(0)
        for row in range(4):
            self.action_full_model.appendRow([self.colormap_full_model.item(row, col).clone() for col in range(4)])
            self.action_table.resizeColumnToContents(row)
        self.action_table.setMinimumWidth(sum([self.action_table.columnWidth(c) for c in range(self.action_full_model.columnCount())]))
        self.action_dev_model = QtGui.QStandardItemModel()
        self.action_dev_model.appendColumn([pass_item.clone(), disc_item.clone(), toggle_item.clone()])
        [self.action_dev_model.appendRow(self.colormap_dev_model.item(l).clone()) for l in range(7)]
        self.action_dir_model = QtGui.QStandardItemModel()
        self.action_dir_model.appendColumn([pass_item.clone(), disc_item.clone(), toggle_item.clone()])
        [self.action_dir_model.appendRow(self.colormap_dir_model.item(l).clone()) for l in range(6)]

        #setting default leds:
        setBold(self.colormap_full_model.item(0, 3))
        setBold(self.colormap_dev_model.item(1))
        setBold(self.colormap_dir_model.item(1))
        setBold(self.action_full_model.item(4, 3))
        setBold(self.action_dev_model.item(9))
        setBold(self.action_dir_model.item(8))


    def color_column_check(self, selected, previous):
        index = self.color_table.selectedIndexes()[0]
        self.led_base_combo.setModelColumn(index.column())
        self.led_base_combo.setCurrentIndex(index.row())

    def action_column_check(self, selected, previous):
        index = self.action_table.selectedIndexes()
        if index:
            self.led_action_combo.setModelColumn(index[0].column())
            self.led_action_combo.setCurrentIndex(index[0].row())
        else:
            print 'What\'s wrong with index? {}'.format(index)
            self.led_action_combo.setModelColumn(0)
            self.led_action_combo.setCurrentIndex(0)

    def enable_set(self, value):
        #TODO: if no patch and no dict value, just clear!
        #maybe we don't need this anymore?
        if not self.current_widget:
            #we need to set these for startup and template change
            if not value:
                self.base_group.setEnabled(value)
                self.patch_group.setEnabled(value)
            return
        self.base_group.setEnabled(value)
        self.patch_group.setEnabled(value)
        self.current_widget['enabled'] = value
        self.tool_group.setEnabled(value)
        self.patch_edit.setStyleSheet('color: {}'.format(patch_colors[self.patch_edit.valid][value]))
        if value:
            patch = self.current_widget.get('patch')
            text = self.current_widget.get('text')
            if not text:
                text = patch if patch else None
            self.labelChanged.emit(self.current_widget['widget'], text if text else True)
        else:
            self.labelChanged.emit(self.current_widget['widget'], False)

    def tool_group_setEnabled(self, value):
        for button in self.tool_group.buttons():
            button.setEnabled(value)
        self.toggle_listview.setEnabled(value)
        if self.current_widget and not isinstance(self.current_widget['widget'], QtGui.QPushButton):
            for button in self.convert_group.buttons():
                button.setEnabled(False)
            self.convert_chk.setEnabled(False)
            self.convert_chk.setChecked(False)
            self.toggle_chk.setEnabled(False)
            self.toggle_chk.setChecked(False)
            toggle_model = QtGui.QStandardItemModel()
            self.toggle_listview.setModel(toggle_model)
        if value:
            self.toggle_range_check()

    def chan_reset(self):
        self.chan_spin.setValue(0)

    def led_reset(self):
        default_led = self.current_widget['widget'].siblingLed
        self.led_combo.setCurrentIndex(default_led+1 if default_led is not None else 0)

    def led_combo_update(self, led):
        if not self.current_widget:
            return
        if led == 0:
            self.led_base_combo.setEnabled(False)
            self.led_action_combo.setEnabled(False)
            if self.current_widget.get('led'):
                if isinstance(self.current_widget['widget'], QtGui.QSlider):
                    self.current_widget.pop('led')
                else:
                    self.current_widget['led'] = False
            return
        self.led_base_combo.setEnabled(True)
        self.led_action_combo.setEnabled(True)
        if led <= 40:
            if self.led_base_combo.model() != self.colormap_full_model:
                self.led_base_combo.setModel(self.colormap_full_model)
                self.led_action_combo.setModel(self.action_full_model)
        elif led <= 44:
            if self.led_base_combo.model() != self.colormap_dev_model:
                self.led_base_combo.setModelColumn(0)
                self.led_base_combo.setModel(self.colormap_dev_model)
                self.led_action_combo.setModelColumn(0)
                self.led_action_combo.setModel(self.action_dev_model)
        else:
            if self.led_base_combo.model() != self.colormap_dir_model:
                self.led_base_combo.setModelColumn(0)
                self.led_base_combo.setModel(self.colormap_dir_model)
                self.led_action_combo.setModelColumn(0)
                self.led_action_combo.setModel(self.action_dir_model)
        for col in range(self.led_base_combo.model().columnCount()):
            self.color_table.resizeColumnToContents(col)
            self.action_table.resizeColumnToContents(col)
        if col == 0:
            self.action_table.setRowHeight(1, self.action_table.rowHeight(0))
            self.action_table.setRowHeight(2, self.action_table.rowHeight(0))
        else:
            small_height = self.action_table.rowHeight(self.action_table.model().rowCount()-1)
            self.action_table.setRowHeight(1, small_height)
            self.action_table.setRowHeight(2, small_height)
        self.color_table.setMinimumWidth(sum([self.color_table.columnWidth(c) for c in range(self.led_base_combo.model().columnCount())]))
        self.action_table.setMinimumWidth(sum([self.action_table.columnWidth(c) for c in range(self.action_full_model.columnCount())]))
        self.current_widget['led'] = led - 1

    def dest_update(self, index):
        if not self.current_widget:
            return
        self.current_widget['dest'] = self.dest_combo.currentIndex()+1

    def text_update(self, text):
        self.current_widget['text'] = str(self.text_edit.text().toLatin1())
        self.labelChanged.emit(self.current_widget['widget'], self.text_edit.text())

    def led_action_update(self, text):
        cols = self.led_action_combo.model().columnCount()
        if cols == 1:
            found = self.led_action_combo.model().findItems('{}'.format(text),  column=0)
            if len(found):
                self.led_action_combo.setCurrentIndex(found[0].row())
        else:
            for c in range(cols):
                found = self.led_action_combo.model().findItems('{}'.format(text),  column=c)
                if len(found):
                    self.led_action_combo.setModelColumn(c)
                    self.led_action_combo.setCurrentIndex(found[0].row())
                    break
        if len(found):
            return
        if self.led_action_combo.currentIndex() >= 0:
            lineEdit = self.led_action_combo.lineEdit()
            pos = lineEdit.cursorPosition()
            self.led_action_combo.setCurrentIndex(-1)
            lineEdit.setText(text)
            lineEdit.setCursorPosition(pos)

    def patch_update(self):
        if not self.current_widget:
            return
        patch = str(self.patch_edit.toPlainText().toLatin1())
        self.current_widget['patch'] = patch
        if len(patch):
            patch_format = patch
            for rep in md_replace:
                patch_format = patch_format.replace(rep, 'md.'+rep)
            try:
                eval(patch_format)
                self.patch_edit.valid = True
            except:
                self.patch_edit.valid = False
        else:
            self.patch_edit.valid = True
        self.patch_edit.setStyleSheet('color: {}'.format(patch_colors[self.patch_edit.valid][self.enable_chk.isChecked()]))
        if self.enable_chk.isChecked():
            if self.text_edit.text():
                self.labelChanged.emit(self.current_widget['widget'], self.text_edit.text())
            else:
                self.labelChanged.emit(self.current_widget['widget'], patch if len(patch) else True)

    def statusbar_create(self):
        self.statusbar.addWidget(QtGui.QLabel('Current mapping:'))
        self.statusbar_empty = QtGui.QLabel('(None)')
        self.statusbar_empty.setEnabled(False)
        self.statusbar.addWidget(self.statusbar_empty)
        etype_edit = QtGui.QLabel('', self.statusbar)
        etype_edit.setFixedWidth(40)
        event_edit = QtGui.QLabel('', self.statusbar)
        event_edit.setFixedWidth(50)
        event_lbl = QtGui.QLabel('event', self.statusbar)
        echan_lbl = QtGui.QLabel('Channel', self.statusbar)
        echan_edit = QtGui.QLabel('', self.statusbar)
        echan_edit.setFixedWidth(12)
        eext_lbl = QtGui.QLabel('Extension', self.statusbar)
        eext_edit = QtGui.QLabel('', self.statusbar)
        eext_edit.setFixedWidth(48)
        emode_lbl = QtGui.QLabel('Mode', self.statusbar)
        emode_edit = QtGui.QLabel('', self.statusbar)
        emode_edit.setFixedWidth(42)
        self.statusbar_edits = [etype_edit, event_edit, echan_edit, eext_edit, emode_edit]
        self.statusbar_labels = [event_lbl, echan_lbl, eext_lbl, emode_lbl]
        self.statusbar.addWidget(etype_edit)
        self.statusbar.addWidget(event_lbl)
        self.statusbar.addWidget(event_edit)
        self.statusbar.addWidget(echan_lbl)
        self.statusbar.addWidget(echan_edit)
        self.statusbar.addWidget(eext_lbl)
        self.statusbar.addWidget(eext_edit)
        self.statusbar.addWidget(emode_lbl)
        self.statusbar.addWidget(emode_edit)
        for widget in self.statusbar_labels:
            widget.hide()
        for widget in self.statusbar_edits:
            widget.hide()
            widget.setFrameStyle(QtGui.QLabel.Sunken)
            widget.setFrameShape(QtGui.QLabel.Panel)

    def status_update(self, event_data):
        if not event_data:
            for widget in self.statusbar_labels+self.statusbar_edits:
                widget.hide()
            self.statusbar_empty.show()
            return
        self.statusbar_empty.hide()
        chan, event_type, data1, ext, mode = event_data
        if ext == True:
            ext = '0-127'
        else:
            ext = '{}-{}'.format(ext[0], ext[1])
        if event_type == md.NOTE:
            data1 = '{} ({})'.format(md.util.note_name(data1), data1)
        event_data = event_type, data1, chan, ext, mode
        for widget in self.statusbar_labels:
            widget.show()
        for i, widget in enumerate(self.statusbar_edits):
            widget.show()
            widget.setText(str(event_data[i]))

    def widget_save(self, template=None):
        if not self.current_widget:
            return
        if not template:
            template = self.main.template
        widget = self.current_widget.get('widget')
        enabled = self.current_widget.get('enabled', True)
#        dest = self.current_widget.get('dest', 1)
        text = self.current_widget.get('text', '')
        self.current_widget['chan'] = self.chan_spin.value()
        convert = self.convert_group.checkedButton().id
        #TODO: not important: consider remembering the state, even if disabled
        if self.convert_chk.isChecked():
            self.current_widget['convert'] = convert
        elif self.current_widget.get('convert'):
            self.current_widget.pop('convert')

        patch = self.current_widget.get('patch')
        if text is not None:
            text = text.strip()
            self.current_widget['text'] = text
        else:
            text = ''
        if len(text):
            pass
        elif patch:
            text = patch
        else:
            text = True
        self.labelChanged.emit(widget, text if enabled else False)
        led_index = self.led_combo.currentIndex()
        if led_index > 0:
            led_item = self.ledlist_model.item(led_index)
            if led_item.led == 0:
                self.current_widget['led'] = False
            elif led_item.led == widget.siblingLed:
                self.current_widget['led'] = True
            led_basevalue = int(str(self.led_base_combo.currentText()), 0)
            if led_basevalue == 0:
                self.current_widget['led_basevalue'] = Disabled
            elif led_item.ledSet == led_basevalue:
                self.current_widget['led_basevalue'] = Enabled
            else:
                self.current_widget['led_basevalue'] = led_basevalue
            led_action = str(self.led_action_combo.currentText())
            if led_action in ['Pass', 'Ignore', 'Toggle']:
                led_action = eval(led_action)
            else:
                try:
                    led_action = int(led_action, 0)
                except:
                    pass
            self.current_widget['led_action'] = led_action

        tooltip = self.main.widget_tooltip(widget, self.current_widget)
        widget.setToolTip(tooltip)
        toggle_model = self.current_widget.get('toggle_model')
        if toggle_model:
            self.current_widget['toggle_values'] = tuple([int(toggle_model.item(i).text()) for i in range(toggle_model.rowCount())])

        self.main.conf_dict[template][widget] = self.current_widget
        self.widgetSaved.emit(template)

    def widget_change(self, widget):
        self.enable_chk.setEnabled(True)
        #save previous widget
        if self.current_widget:
#            print self.current_widget
            if self.current_widget['widget'] == widget:
                return
            self.widget_save()

        if not self.isVisible():
            return
        #Prepare editor window
        self.status_update(self.main.map_dict[self.main.template].get(widget))
        self.base_group.setTitle('Base configuration: {}'.format(widget.readable))
        led_index = self.led_combo.currentIndex()
        led_item = self.ledlist_model.item(led_index, 0)
        setBold(led_item, False)
        if widget.siblingLed is not None:
            setBold(self.ledlist_model.item(widget.siblingLed+1))
        else:
            setBold(self.ledlist_model.item(0))
        widget_dict = self.main.conf_dict[self.main.template][widget]
        if widget_dict == None:
            self.current_widget = {'widget': widget, 'enabled': False}
            self.enable_chk.setChecked(False)
            self.dest_combo.setCurrentIndex(0)
            self.patch_edit.setPlainText('')
            siblingLed = widget.siblingLed
            if siblingLed is not None:
                self.led_combo.setCurrentIndex(siblingLed+1 if siblingLed is not None else 0)
                if siblingLed < 40:
                    self.led_base_combo.setModelColumn(3)
                    self.led_base_combo.setCurrentIndex(0)
                    self.led_action_combo.setModelColumn(0)
                    self.led_action_combo.setCurrentIndex(0)
                else:
                    self.led_base_combo.setModelColumn(0)
                    self.led_base_combo.setCurrentIndex(1)
                    self.led_action_combo.setModelColumn(0)
                    self.led_action_combo.setCurrentIndex(1)
            #other values stuff to reset
            return

        widget_dict['widget'] = widget
        enabled = widget_dict.get('enabled', True)
        self.current_widget = widget_dict
        if enabled and self.enable_chk.isChecked():
                self.tool_group.setEnabled(True)
        self.enable_chk.setChecked(enabled)

        #Destination port
        dest = widget_dict.get('dest', 1)-1
        self.dest_combo.blockSignals(True)
        if dest == None:
            self.dest_combo.setCurrentIndex(0)
        else:
            if dest >= self.output_model.rowCount():
                dest = self.output_model.rowCount()-1
            self.dest_combo.setCurrentIndex(dest)
        self.dest_combo.blockSignals(False)

        #Text
        text = widget_dict.get('text', '')
        self.text_edit.setText(text)

        #Destination channel
        chan = widget_dict.get('chan')
        if chan == None:
            self.chan_spin.setValue(0)
        else:
            self.chan_spin.setValue(chan)

        #Convert event type
        convert = widget_dict.get('convert')
        if convert == None:
            self.convert_chk.setChecked(False)
            self.convert_ctrl_radio.setChecked(True)
        else:
            self.convert_chk.setChecked(True)
            if convert == ToCtrl:
                self.convert_ctrl_radio.setChecked(True)
            else:
                self.convert_note_radio.setChecked(True)

        #Patch
        patch = widget_dict.get('patch')
        if patch:
#            self.patch_edit.setStyleSheet('color: black')
            self.patch_edit.setPlainText(str(patch))
        elif enabled:
            self.patch_edit.blockSignals(True)
            self.patch_edit.setStyleSheet('color: gray')
            self.patch_edit.setPlainText('Pass()')
            self.patch_edit.valid = True
            self.patch_edit.blockSignals(False)

        #LED
        led = widget_dict.get('led', True)
        self.led_combo.blockSignals(True)
        if led == None or (isinstance(led, bool) and led == False):
            self.led_combo.setCurrentIndex(0)
        #TODO: maybe we can use Enabled and Disabled?
        elif isinstance(led, bool) and led == True:
            self.led_combo.setCurrentIndex(widget.siblingLed+1 if widget.siblingLed is not None else 0)
        else:
            self.led_combo.setCurrentIndex(led+1)
        self.led_combo.blockSignals(False)
        #we block signals, just to be sure to emit one and one only
#        self.led_combo.currentIndexChanged.emit(self.led_combo.currentIndex())
        self.led_combo_update(self.led_combo.currentIndex())

        led_basevalue = widget_dict.get('led_basevalue', Enabled)
        cols = self.led_base_combo.model().columnCount()
        if led_basevalue in [None, Disabled]:
            self.led_base_combo.setModelColumn(0)
            self.led_base_combo.setCurrentIndex(0)
        else:
            if led_basevalue == Enabled:
                if cols == 1:
                    self.led_base_combo.setModelColumn(0)
                    self.led_base_combo.setCurrentIndex(1)
                else:
                    self.led_base_combo.setModelColumn(3)
                    self.led_base_combo.setCurrentIndex(0)
            else:
                if cols == 1:
#                    self.led_base_combo.setModelColumn(0)
                    found = self.led_base_combo.model().findItems('0x{:02x}'.format(led_basevalue),  column=0)
                    if len(found):
                        self.led_base_combo.setCurrentIndex(found[0].row())
                    else:
                        self.led_base_combo.setCurrentIndex(1)
                else:
                    is_found = False
                    for c in range(cols):
                        found = self.led_base_combo.model().findItems('0x{:02x}'.format(led_basevalue),  column=c)
                        if len(found):
                            self.led_base_combo.setModelColumn(c)
                            self.led_base_combo.setCurrentIndex(found[0].row())
                            is_found = True
                            break
                    if not is_found:
                        self.led_base_combo.setModelColumn(3)
                        self.led_base_combo.setCurrentIndex(0)
        led_action = widget_dict.get('led_action', Pass)
        if led_action == Pass:
            self.led_action_combo.setModelColumn(0)
            self.led_action_combo.setCurrentIndex(0)
        elif led_action == Ignore:
            if cols == 1:
#                self.led_action_combo.setModelColumn(0)
                self.led_action_combo.setCurrentIndex(1)
            else:
                self.led_action_combo.setModelColumn(1)
                self.led_action_combo.setCurrentIndex(0)
        elif led_action == Toggle:
            if cols == 1:
                self.led_action_combo.setCurrentIndex(2)
            else:
                self.led_action_combo.setModelColumn(2)
                self.led_action_combo.setCurrentIndex(0)
        elif isinstance(led_action, int):
            if cols == 1:
                found = self.led_action_combo.model().findItems('{}'.format(hex(led_action)),  column=0)
                if len(found):
                    self.led_action_combo.setCurrentIndex(found[0].row())
                else:
                    self.led_action_combo.lineEdit().setText(led_action)
            else:
                is_found = False
                for c in range(cols):
                    found = self.led_action_combo.model().findItems('{}'.format(hex(led_action)),  column=c)
                    if len(found):
                        self.led_action_combo.setModelColumn(c)
                        self.led_action_combo.setCurrentIndex(found[0].row())
                        is_found = True
                        break
                if not is_found:
                    self.led_action_combo.setModelColumn(0)
                    self.led_action_combo.setCurrentIndex(-1)
                    self.led_action_combo.lineEdit().setText(led_action)
        else:
            self.led_action_combo.lineEdit().setText(led_action)

        #Toggle
        if not isinstance(widget, QtGui.QPushButton):
            self.toggle_chk.setChecked(False)
            self.toggle_chk.setEnabled(False)
            toggle_model = QtGui.QStandardItemModel()
        else:
#            self.toggle_chk.setEnabled(True)
            toggle = self.current_widget.get('toggle', False)
            if toggle:
                self.toggle_chk.setChecked(True)
            else:
                self.toggle_chk.setChecked(False)
            toggle_model = self.current_widget.get('toggle_model')
            if not toggle_model:
                toggle_values = self.current_widget.get('toggle_values')
                toggle_model = QtGui.QStandardItemModel()
                if toggle_values:
                    for i in toggle_values:
                        item = QtGui.QStandardItem(str(i))
                        item.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsDragEnabled)
                        toggle_model.appendRow(item)
                    self.current_widget['toggle'] = self.current_widget.get('toggle', True)
                    self.current_widget['toggle_model'] = toggle_model
        self.toggle_listview.setModel(toggle_model)


    def patch_edit_focusIn(self, event):
        QtGui.QPlainTextEdit.focusInEvent(self.patch_edit, event)
        patch = self.current_widget.get('patch')
        if not patch:
            self.patch_edit.setPlainText('')

    def patch_edit_focusOut(self, event):
        QtGui.QPlainTextEdit.focusOutEvent(self.patch_edit, event)
        patch = self.current_widget.get('patch')
        if not patch:
            self.patch_edit.blockSignals(True)
            self.patch_edit.setStyleSheet('color: gray')
            self.patch_edit.setPlainText('Pass')
            self.patch_edit.blockSignals(False)
