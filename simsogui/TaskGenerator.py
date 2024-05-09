from PyQt5.QtGui import QRegExpValidator
from PyQt5.QtWidgets import QCheckBox, QComboBox, QDialogButtonBox, QDialog, QDoubleSpinBox, QGroupBox, QHBoxLayout, \
    QLabel, QLineEdit, QMessageBox, QRadioButton, QSlider, QSpinBox, QVBoxLayout, QWidget
from PyQt5.QtCore import pyqtSignal, QRegExp
from PyQt5 import QtCore, QtWidgets
from simso.generator.task_generator import StaffordRandFixedSum, \
    gen_periods_loguniform, gen_periods_uniform, gen_periods_discrete, \
    gen_tasksets, UUniFastDiscard, gen_kato_utilizations


class _DoubleSlider(QSlider):
    doubleValueChanged = pyqtSignal([float])

    def __init__(self, orient, parent):
        QSlider.__init__(self, orient, parent)

        self.valueChanged.connect(
            lambda x: self.doubleValueChanged.emit(x / 100.0))

    def setMinimum(self, val):
        QSlider.setMinimum(self, val * 100)

    def setMaximum(self, val):
        QSlider.setMaximum(self, val * 100)

    def setValue(self, val):
        QSlider.setValue(self, int(val * 100))


class IntervalSpinner(QWidget):
    def __init__(self, parent, min_=1, max_=1000, step=1, round_option=True):
        QWidget.__init__(self, parent)
        layout = QVBoxLayout(self)
        hlayout = QHBoxLayout()
        self.start = QDoubleSpinBox(self)
        self.start.setMinimum(min_)
        self.start.setMaximum(max_)
        self.end = QDoubleSpinBox(self)
        self.end.setMinimum(min_)
        self.end.setMaximum(max_)
        self.end.setValue(max_)
        self.start.setSingleStep(step)
        self.end.setSingleStep(step)

        self.start.valueChanged.connect(self.on_value_start_changed)
        self.end.valueChanged.connect(self.on_value_end_changed)

        hlayout.addWidget(self.start)
        hlayout.addWidget(self.end)
        layout.addLayout(hlayout)

        if round_option:
            self.integerCheckBox = QCheckBox("Round to integer values", self)
            layout.addWidget(self.integerCheckBox)

    def on_value_start_changed(self, val):
        if self.end.value() < val:
            self.end.setValue(val)

    def on_value_end_changed(self, val):
        if self.start.value() > val:
            self.start.setValue(val)

    def getMin(self):
        return self.start.value()

    def getMax(self):
        return self.end.value()

    def getRound(self):
        return self.integerCheckBox.isChecked()


class TaskGeneratorDialog(QDialog):
    def __init__(self, nbprocessors):
        QDialog.__init__(self)
        self.layout = QVBoxLayout(self)
        self.taskset = None
        self.nbprocessors = nbprocessors

        # Utilizations:
        vbox_utilizations = QVBoxLayout()
        group = QGroupBox("Task Utilizations:")

        hbox_class = QHBoxLayout()
        hbox_class.addWidget(QLabel("Task class:", self))
        self.comboTaskClass = QComboBox()
        self.comboTaskClass.addItem("Generic")
        self.comboTaskClass.addItem("Mixed-Criticality")
        self.comboTaskClass.currentIndexChanged.connect(self.class_changed)
        hbox_class.addWidget(self.comboTaskClass)
        vbox_utilizations.addLayout(hbox_class)

        # Number of criticality levels:
        self.hbox_nr_crit_levels = QHBoxLayout()
        self.spin_nr_crit_levels = QSpinBox(self)
        self.spin_nr_crit_levels.setMinimum(2)
        self.spin_nr_crit_levels.setMaximum(10)  # That's arbitrary.
        self.hbox_nr_crit_levels.addWidget(QLabel("Number of MC levels: ", self))
        self.hbox_nr_crit_levels.addStretch(1)
        self.hbox_nr_crit_levels.addWidget(self.spin_nr_crit_levels)
        self.spin_nr_crit_levels.valueChanged.connect(self.nr_crit_levels_changed)
        vbox_utilizations.addLayout(self.hbox_nr_crit_levels)

        hbox = QHBoxLayout()
        hbox.addWidget(QLabel("Generator:", self))
        self.comboGenerator = QComboBox()
        self.comboGenerator.addItem("RandFixedSum")
        self.comboGenerator.addItem("UUniFast-Discard")
        self.comboGenerator.addItem("Kato's method")
        self.comboGenerator.currentIndexChanged.connect(self.generator_changed)
        hbox.addWidget(self.comboGenerator)
        vbox_utilizations.addLayout(hbox)

        # Load slider + spinner:
        self.hbox_load = QHBoxLayout()
        sld = _DoubleSlider(QtCore.Qt.Horizontal, self)
        sld.setMinimum(0)
        sld.setMaximum(32)
        self.spin_load = QDoubleSpinBox(self)
        self.spin_load.setMinimum(0)
        self.spin_load.setMaximum(32)
        self.spin_load.setSingleStep(0.1)
        self.hbox_load.addWidget(QLabel("Total utilization: ", self))
        self.hbox_load.addWidget(sld)
        self.hbox_load.addWidget(self.spin_load)
        sld.doubleValueChanged.connect(self.spin_load.setValue)
        self.spin_load.valueChanged.connect(sld.setValue)
        self.spin_load.setValue(self.nbprocessors / 2.)
        vbox_utilizations.addLayout(self.hbox_load)

        # Number of periodic tasks:
        self.hbox_tasks = QHBoxLayout()
        self.spin_tasks = QSpinBox(self)
        self.spin_tasks.setMinimum(0)
        self.spin_tasks.setMaximum(999)  # That's arbitrary.
        self.hbox_tasks.addWidget(QLabel("Number of periodic tasks: ", self))
        self.hbox_tasks.addStretch(1)
        self.hbox_tasks.addWidget(self.spin_tasks)
        vbox_utilizations.addLayout(self.hbox_tasks)

        # Number of sporadic tasks:
        self.hbox_sporadic_tasks = QHBoxLayout()
        self.spin_sporadic_tasks = QSpinBox(self)
        self.spin_sporadic_tasks.setMinimum(0)
        self.spin_sporadic_tasks.setMaximum(999)  # That's arbitrary.
        self.hbox_sporadic_tasks.addWidget(
            QLabel("Number of sporadic tasks: ", self))
        self.hbox_sporadic_tasks.addStretch(1)
        self.hbox_sporadic_tasks.addWidget(self.spin_sporadic_tasks)
        vbox_utilizations.addLayout(self.hbox_sporadic_tasks)

        self.mc_vbox_utilizations = QVBoxLayout()
        vbox_utilizations.addLayout(self.mc_vbox_utilizations)

        self.mc_vbox_periodic_tasks = QVBoxLayout()
        vbox_utilizations.addLayout(self.mc_vbox_periodic_tasks)
        self.mc_vbox_sporadic_tasks = QVBoxLayout()
        vbox_utilizations.addLayout(self.mc_vbox_sporadic_tasks)

        # Min / Max utilizations
        self.hbox_utilizations = QHBoxLayout()
        self.hbox_utilizations.addWidget(QLabel("Min/Max utilizations: ",
                                                self))
        self.interval_utilization = IntervalSpinner(
            self, min_=0, max_=1, step=.01, round_option=False)
        self.hbox_utilizations.addWidget(self.interval_utilization)
        vbox_utilizations.addLayout(self.hbox_utilizations)

        group.setLayout(vbox_utilizations)
        self.layout.addWidget(group)

        # Periods:
        vbox_periods = QVBoxLayout()
        group = QGroupBox("Task Periods:")

        # Log uniform
        self.lunif = QRadioButton("log-uniform distribution between:")
        vbox_periods.addWidget(self.lunif)
        self.lunif.setChecked(True)

        self.lunif_interval = IntervalSpinner(self)
        self.lunif_interval.setEnabled(self.lunif.isChecked())
        self.lunif.toggled.connect(self.lunif_interval.setEnabled)
        vbox_periods.addWidget(self.lunif_interval)

        # Uniform
        self.unif = QRadioButton("uniform distribution between:")
        vbox_periods.addWidget(self.unif)

        self.unif_interval = IntervalSpinner(self)
        self.unif_interval.setEnabled(self.unif.isChecked())
        self.unif.toggled.connect(self.unif_interval.setEnabled)
        vbox_periods.addWidget(self.unif_interval)

        # Discrete
        discrete = QRadioButton("chosen among these (space separated) values:")
        vbox_periods.addWidget(discrete)

        self.periods = QLineEdit(self)
        self.periods.setValidator(QRegExpValidator(
            QRegExp("^\\d*(\.\\d*)?( \\d*(\.\\d*)?)*$")))

        vbox_periods.addWidget(self.periods)
        self.periods.setEnabled(discrete.isChecked())
        discrete.toggled.connect(self.periods.setEnabled)
        vbox_periods.addStretch(1)

        group.setLayout(vbox_periods)
        self.layout.addWidget(group)

        buttonBox = QDialogButtonBox()
        cancel = buttonBox.addButton(QDialogButtonBox.Cancel)
        generate = buttonBox.addButton("Generate", QDialogButtonBox.AcceptRole)
        cancel.clicked.connect(self.reject)
        generate.clicked.connect(self.generate)
        self.layout.addWidget(buttonBox)

        self.show_randfixedsum_options()
        self.show_generic_options()

    def class_changed(self, value):
        if value == 1:
            self.show_mixed_criticality_options()
        else:
            self.show_generic_options()

    def nr_crit_levels_changed(self, value):
        for i in range(self.mc_vbox_utilizations.count()):
            if self.mc_vbox_utilizations.itemAt(i).widget():
                self.mc_vbox_utilizations.itemAt(i).widget().deleteLater()
            if self.mc_vbox_utilizations.itemAt(i).layout():
                for j in range(self.mc_vbox_utilizations.itemAt(i).layout().count()):
                    if self.mc_vbox_utilizations.itemAt(i).layout().itemAt(j).widget():
                        self.mc_vbox_utilizations.itemAt(i).layout().itemAt(j).widget().deleteLater()
        for i in reversed(range(self.mc_vbox_periodic_tasks.count())):
            if self.mc_vbox_periodic_tasks.itemAt(i).widget():
                self.mc_vbox_periodic_tasks.itemAt(i).widget().deleteLater()
            if self.mc_vbox_periodic_tasks.itemAt(i).layout():
                for j in range(self.mc_vbox_periodic_tasks.itemAt(i).layout().count()):
                    if self.mc_vbox_periodic_tasks.itemAt(i).layout().itemAt(j).widget():
                        self.mc_vbox_periodic_tasks.itemAt(i).layout().itemAt(j).widget().deleteLater()
        for i in range(self.mc_vbox_sporadic_tasks.count()):
            if self.mc_vbox_sporadic_tasks.itemAt(i).widget():
                self.mc_vbox_sporadic_tasks.itemAt(i).widget().deleteLater()
            if self.mc_vbox_sporadic_tasks.itemAt(i).layout():
                for j in range(self.mc_vbox_sporadic_tasks.itemAt(i).layout().count()):
                    if self.mc_vbox_sporadic_tasks.itemAt(i).layout().itemAt(j).widget():
                        self.mc_vbox_sporadic_tasks.itemAt(i).layout().itemAt(j).widget().deleteLater()

        self.mc_vbox_periodic_tasks.addWidget(
            QLabel("Number of periodic tasks:", self))
        self.mc_vbox_sporadic_tasks.addWidget(
            QLabel("Number of sporadic tasks:", self))
        for i in range(value):
            load_name = "hbox_mc_load_{}".format(i)
            setattr(self, load_name, QHBoxLayout())
            load = getattr(self, load_name)

            spin_load_name = "spin_mc_load_{}".format(i)
            setattr(self, spin_load_name, QDoubleSpinBox(self))
            spin_load = getattr(self, spin_load_name)

            sld = _DoubleSlider(QtCore.Qt.Horizontal, self)
            sld.setMinimum(0)
            sld.setMaximum(32)
            spin_load.setMinimum(0)
            spin_load.setMaximum(32)
            spin_load.setSingleStep(0.1)
            load.addWidget(QLabel("Total utilization (MC level {}): ".format(i), self))
            load.addWidget(sld)
            load.addWidget(spin_load)
            sld.doubleValueChanged.connect(spin_load.setValue)
            spin_load.valueChanged.connect(sld.setValue)
            spin_load.setValue(self.nbprocessors / 2.)
            self.mc_vbox_utilizations.addLayout(load)

            hbox_name = "hbox_mc_tasks_{}".format(i)
            setattr(self, hbox_name, QHBoxLayout())
            hbox = getattr(self, hbox_name)

            spin_name = "spin_mc_tasks_{}".format(i)
            setattr(self, spin_name, QSpinBox(self))
            spin_tasks = getattr(self, spin_name)

            spin_tasks.setMinimum(0)
            spin_tasks.setMaximum(999)  # That's arbitrary.
            hbox.addWidget(QLabel("MC level: {}".format(i), self))
            hbox.addStretch(1)
            hbox.addWidget(spin_tasks)
            self.mc_vbox_periodic_tasks.addLayout(hbox)

            sporadic_hbox_name = "hbox_mc_sporadic_tasks_{}".format(i)
            setattr(self, sporadic_hbox_name, QHBoxLayout())
            sporadic_hbox = getattr(self, sporadic_hbox_name)

            sporadic_spin_name = "spin_mc_sporadic_tasks_{}".format(i)
            setattr(self, sporadic_spin_name, QSpinBox(self))
            sporadic_spin = getattr(self, sporadic_spin_name)

            sporadic_spin.setMinimum(0)
            sporadic_spin.setMaximum(999)  # That's arbitrary.
            sporadic_hbox.addWidget(QLabel("MC level: {}".format(i), self))
            sporadic_hbox.addStretch(1)
            sporadic_hbox.addWidget(sporadic_spin)
            self.mc_vbox_sporadic_tasks.addLayout(sporadic_hbox)

    def generator_changed(self, value):
        if value == 2:
            self.show_kato_options()
        else:
            self.show_randfixedsum_options()

    def get_nr_crit_levels(self):
        return self.spin_nr_crit_levels.value()

    def get_task_class(self):
        return self.comboTaskClass.currentText()

    def show_mixed_criticality_options(self):
        for i in range(self.hbox_nr_crit_levels.count()):
            if self.hbox_nr_crit_levels.itemAt(i).widget():
                self.hbox_nr_crit_levels.itemAt(i).widget().show()
        for i in range(self.mc_vbox_periodic_tasks.count()):
            if self.mc_vbox_periodic_tasks.itemAt(i).widget():
                self.mc_vbox_periodic_tasks.itemAt(i).widget().show()
        for i in range(self.mc_vbox_sporadic_tasks.count()):
            if self.mc_vbox_sporadic_tasks.itemAt(i).widget():
                self.mc_vbox_sporadic_tasks.itemAt(i).widget().show()
        for i in range(self.mc_vbox_utilizations.count()):
            if self.mc_vbox_utilizations.itemAt(i).widget():
                self.mc_vbox_utilizations.itemAt(i).widget().show()
        for i in range(self.hbox_load.count()):
            if self.hbox_load.itemAt(i).widget():
                self.hbox_load.itemAt(i).widget().hide()
        for i in range(self.hbox_tasks.count()):
            if self.hbox_tasks.itemAt(i).widget():
                self.hbox_tasks.itemAt(i).widget().hide()
        for i in range(self.hbox_sporadic_tasks.count()):
            if self.hbox_sporadic_tasks.itemAt(i).widget():
                self.hbox_sporadic_tasks.itemAt(i).widget().hide()

    def show_generic_options(self):
        for i in range(self.hbox_nr_crit_levels.count()):
            if self.hbox_nr_crit_levels.itemAt(i).widget():
                self.hbox_nr_crit_levels.itemAt(i).widget().hide()
        for i in range(self.mc_vbox_periodic_tasks.count()):
            if self.mc_vbox_periodic_tasks.itemAt(i).widget():
                self.mc_vbox_periodic_tasks.itemAt(i).widget().hide()
        for i in range(self.mc_vbox_sporadic_tasks.count()):
            if self.mc_vbox_sporadic_tasks.itemAt(i).widget():
                self.mc_vbox_sporadic_tasks.itemAt(i).widget().hide()
        for i in range(self.mc_vbox_utilizations.count()):
            if self.mc_vbox_utilizations.itemAt(i).widget():
                self.mc_vbox_utilizations.itemAt(i).widget().hide()
        for i in range(self.hbox_load.count()):
            if self.hbox_load.itemAt(i).widget():
                self.hbox_load.itemAt(i).widget().show()
        for i in range(self.hbox_tasks.count()):
            if self.hbox_tasks.itemAt(i).widget():
                self.hbox_tasks.itemAt(i).widget().show()
        for i in range(self.hbox_sporadic_tasks.count()):
            if self.hbox_sporadic_tasks.itemAt(i).widget():
                self.hbox_sporadic_tasks.itemAt(i).widget().show()

    def show_randfixedsum_options(self):
        for i in range(self.hbox_utilizations.count()):
            self.hbox_utilizations.itemAt(i).widget().hide()
        for i in range(self.hbox_tasks.count()):
            if self.hbox_tasks.itemAt(i).widget():
                self.hbox_tasks.itemAt(i).widget().show()
        for i in range(self.hbox_sporadic_tasks.count()):
            if self.hbox_sporadic_tasks.itemAt(i).widget():
                self.hbox_sporadic_tasks.itemAt(i).widget().show()

    def show_kato_options(self):
        for i in range(self.hbox_utilizations.count()):
            if self.hbox_utilizations.itemAt(i).widget():
                self.hbox_utilizations.itemAt(i).widget().show()
        for i in range(self.hbox_tasks.count()):
            if self.hbox_tasks.itemAt(i).widget():
                self.hbox_tasks.itemAt(i).widget().hide()
        for i in range(self.hbox_sporadic_tasks.count()):
            if self.hbox_sporadic_tasks.itemAt(i).widget():
                self.hbox_sporadic_tasks.itemAt(i).widget().hide()

    def get_min_utilization(self):
        return self.interval_utilization.getMin()

    def get_max_utilization(self):
        return self.interval_utilization.getMax()

    def get_mc_utilizations(self):
        utilizations = []
        for i in range(self.mc_vbox_utilizations.count()):
            if self.mc_vbox_utilizations.itemAt(i).layout():
                inner_layout = self.mc_vbox_utilizations.itemAt(i).layout()
                for j in range(inner_layout.count()):
                    if inner_layout.itemAt(j).widget() and type(inner_layout.itemAt(j).widget()) == QDoubleSpinBox:
                        utilizations.append(inner_layout.itemAt(j).widget().value())

        return utilizations

    def get_nr_mc_periodic_tasks(self):
        nr_tasks = []
        for i in range(self.mc_vbox_periodic_tasks.count()):
            if self.mc_vbox_periodic_tasks.itemAt(i).layout():
                inner_layout = self.mc_vbox_periodic_tasks.itemAt(i).layout()
                for j in range(inner_layout.count()):
                    if inner_layout.itemAt(j).widget() and type(inner_layout.itemAt(j).widget()) == QSpinBox:
                        nr_tasks.append(inner_layout.itemAt(j).widget().value())

        return nr_tasks

    def get_nr_mc_sporadic_tasks(self):
        nr_tasks = []
        for i in range(self.mc_vbox_sporadic_tasks.count()):
            if self.mc_vbox_sporadic_tasks.itemAt(i).layout():
                inner_layout = self.mc_vbox_sporadic_tasks.itemAt(i).layout()
                for j in range(inner_layout.count()):
                    if inner_layout.itemAt(j).widget() and type(inner_layout.itemAt(j).widget()) == QSpinBox:
                        nr_tasks.append(inner_layout.itemAt(j).widget().value())

        return nr_tasks

    def get_mc_nb_tasks(self):
        return sum(self.get_nr_mc_periodic_tasks()) + sum(self.get_nr_mc_sporadic_tasks())

    def generate_taskset(self, n):
        if self.comboGenerator.currentIndex() == 0:
            u = StaffordRandFixedSum(n, self.get_utilization(), 1)
        elif self.comboGenerator.currentIndex() == 1:
            u = UUniFastDiscard(n, self.get_utilization(), 1)
        else:
            u = gen_kato_utilizations(1, self.get_min_utilization(),
                                      self.get_max_utilization(),
                                      self.get_utilization())
            n = len(u[0])

        p_types = self.get_periods()
        if p_types[0] == "unif":
            p = gen_periods_uniform(n, 1, p_types[1], p_types[2], p_types[3])
        elif p_types[0] == "lunif":
            p = gen_periods_loguniform(n, 1, p_types[1], p_types[2],
                                       p_types[3])
        else:
            p = gen_periods_discrete(n, 1, p_types[1])

        if u and p:
            self.taskset = gen_tasksets(u, p)[0]
            self.accept()
        elif not u:
            QMessageBox.warning(
                self, "Generation failed",
                "Please check the utilization and the number of tasks.")
        else:
            QMessageBox.warning(
                self, "Generation failed",
                "Pleache check the periods.")

    def generate_mc_taskset(self, u, n, crit_level=None):
        if self.comboGenerator.currentIndex() == 0:
            u = StaffordRandFixedSum(n, u, 1)
        elif self.comboGenerator.currentIndex() == 1:
            u = UUniFastDiscard(n, u, 1)

        p_types = self.get_periods()
        if p_types[0] == "unif":
            p = gen_periods_uniform(n, 1, p_types[1], p_types[2], p_types[3])
        elif p_types[0] == "lunif":
            p = gen_periods_loguniform(n, 1, p_types[1], p_types[2],
                                       p_types[3])
        else:
            p = gen_periods_discrete(n, 1, p_types[1])

        if u and p:
            return gen_tasksets(u, p, crit_level)[0]
        elif not u:
            QMessageBox.warning(
                self, "Generation failed",
                "Please check the utilization and the number of tasks.")
        else:
            QMessageBox.warning(
                self, "Generation failed",
                "Please check the periods.")

    def generate(self):
        if self.get_task_class() == "Generic":
            n = self.get_nb_tasks()
            if (n == 0):
                QMessageBox.warning(
                    self, "Generation failed",
                    "Please check the utilization and the number of tasks.")
                return

            self.generate_taskset(n)
        else:
            mc_periodic_tasks = self.get_nr_mc_periodic_tasks()
            mc_sporadic_tasks = self.get_nr_mc_sporadic_tasks()
            mc_utilizations = self.get_mc_utilizations()
            if sum(mc_periodic_tasks) + sum(mc_sporadic_tasks) == 0:
                QMessageBox.warning(
                    self, "Generation failed",
                    "Please check the utilization and the number of tasks.")
                return

            for i in range(self.get_nr_crit_levels()):
                nb_tasks = mc_periodic_tasks[i] + mc_sporadic_tasks[i]
                if not self.taskset:
                    self.taskset = self.generate_mc_taskset(mc_utilizations[i], nb_tasks, i)
                else:
                    self.taskset.extend(self.generate_mc_taskset(mc_utilizations[i], nb_tasks, i))

            self.accept()

    def get_nb_tasks(self):
        return self.spin_tasks.value() + self.spin_sporadic_tasks.value()

    def get_nb_periodic_tasks(self):
        return self.spin_tasks.value()

    def get_nb_sporadic_tasks(self):
        return self.spin_sporadic_tasks.value()

    def get_utilization(self):
        return self.spin_load.value()

    def get_periods(self):
        if self.unif.isChecked():
            return ("unif", self.unif_interval.getMin(),
                    self.unif_interval.getMax(), self.unif_interval.getRound())
        elif self.lunif.isChecked():
            return ("lunif", self.lunif_interval.getMin(),
                    self.lunif_interval.getMax(),
                    self.lunif_interval.getRound())
        else:
            return ("discrete", map(float, str(self.periods.text()).split()))


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    ex = TaskGeneratorDialog(5)
    if ex.exec_():
        print(ex.taskset)
