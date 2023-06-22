from PyQt5.QtWidgets import QDialog, QApplication, QMainWindow, QFileDialog
from PyQt5.QtCore import QObject, QThreadPool, pyqtSignal, QRunnable, QThread

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from cpsMainWindow import Ui_cpsMainWindow
from cpsRecord import Ui_recordDialog

from matplotlib.widgets import SpanSelector
from numpy.ma import multiply
from scipy.io import wavfile
from scipy import signal
import pyaudio
import time
import wave
import sys
import os

class workerSignals(QObject):
    finished = pyqtSignal()
    progress = pyqtSignal(int)

class workerRecord(QRunnable):
    def __init__(self, length, filename):
        super(workerRecord, self).__init__()
        self.signals = workerSignals()
        self.length = length
        self.filename = filename + '.wav'

    def run(self):
        CHUNK = 1024
        FORMAT = pyaudio.paInt16
        CHANNELS = 1
        RATE = 44100
        RECORD_SECONDS = self.length
        WAVE_OUTPUT_FILENAME = self.filename

        p = pyaudio.PyAudio()

        stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)

        frames = []

        for i in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
            data = stream.read(CHUNK)
            frames.append(data)

        stream.stop_stream()
        stream.close()
        p.terminate()

        wf = wave.open(WAVE_OUTPUT_FILENAME, 'wb')
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(p.get_sample_size(FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(b''.join(frames))
        wf.close()

        self.signals.finished.emit()

class workerTime(QRunnable):
    def __init__(self, length):
        super(workerTime, self).__init__()
        self.signals = workerSignals()
        self.length = length

    def run(self):
        while self.length > 0:
            self.signals.progress.emit(self.length)
            time.sleep(1)
            self.length -= 1
            self.signals.progress.emit(self.length)

        self.signals.finished.emit()

class recordWindow(Ui_recordDialog):
    def __init__(self, Dialog):
        super(recordWindow, self).setupUi(Dialog)

    def setupUiRecord(self, Dialog):
        self.quitButton.clicked.connect(Dialog.reject)
        self.chooseButton.clicked.connect(self.getDirectory)
        self.recStopButton.clicked.connect(self.runRecStop)
        self.stringPath = ''

    def getDirectory(self):
        chosenPath = str(QFileDialog.getExistingDirectory(cpsMainWindow, caption="Select Directory"))
        if chosenPath!="":
            self.pathBrowser.setText(chosenPath)
            self.stringPath = chosenPath

    def thread_complete(self):
        self.recStopButton.setEnabled(True)
        self.recStopButton.setText('Record')
        self.quitButton.setEnabled(True)

    def thread_progress(self, i):
        self.recStopButton.setText(str(i) + 's')

    def runRecStop(self):
        if self.stringPath != '' and self.filenameInput.text() != '':

            self.threadpool = QThreadPool()
            input = self.filenameInput.text()
            input = input.split('.',1)[0]

            self.recStopButton.setEnabled(False)
            self.quitButton.setEnabled(False)

            self.threadRecord = QThread()
            self.threadTime = QThread()
            self.workerRecord = workerRecord(self.lengthSpinBox.value(), input)
            self.workerTime = workerTime(self.lengthSpinBox.value())

            self.workerRecord.signals.finished.connect(self.thread_complete)
            self.workerRecord.signals.finished.connect(self.threadRecord.deleteLater)
            self.workerRecord.signals.finished.connect(self.workerRecord.signals.deleteLater)
            self.workerTime.signals.finished.connect(self.thread_complete)
            self.workerTime.signals.finished.connect(self.threadTime.deleteLater)
            self.workerTime.signals.finished.connect(self.workerTime.signals.deleteLater)
            self.workerTime.signals.progress.connect(self.thread_progress)

            self.threadpool.start(self.workerRecord)
            self.threadpool.start(self.workerTime)

class Ui_cpsApp(Ui_cpsMainWindow):
    def __init__(self):
        super(Ui_cpsApp, self).__init__()

    def setupUiApp(self, MainWindow):
        super(Ui_cpsApp, self).setupUi(MainWindow)

        self.filePath = ""
        self.colorMap = 'magma'
        self.color = 'orange'

        self.populateComboBoxes()
        self.nfftComboBox.activated.connect(self.clicker)
        self.scaleComboBox.activated.connect(self.activateComboBoxes)
        self.minFreqComboBox.activated.connect(self.activateComboBoxes)
        self.maxFreqComboBox.activated.connect(self.activateComboBoxes)
        self.noverlapComboBox.activated.connect(self.activateComboBoxes)
        self.windowComboBox.activated.connect(self.activateComboBoxes)

        self.actionRecord.triggered.connect(self.runRecord)
        self.actionChoose.triggered.connect(self.getDirectory)

        self.actionViridis.triggered.connect(self.triggeredViridis)
        self.actionInferno.triggered.connect(self.triggeredInferno)
        self.actionMagma.triggered.connect(self.triggeredMagma)
        self.actionRdBu.triggered.connect(self.triggeredRdBu)
        self.actionOrange.triggered.connect(self.triggeredOrange)
        self.actionBlack.triggered.connect(self.triggeredBlack)
        self.actionBlue.triggered.connect(self.triggeredBlue)
        self.actionRed.triggered.connect(self.triggeredRed)
        self.actionBroad.triggered.connect(self.triggeredBroad)
        self.actionAccurate.triggered.connect(self.triggeredAccurate)
        self.actionRemove_span.triggered.connect(self.triggeredRemoveSpan)
        self.actionQuitApp.triggered.connect(MainWindow.close)

        self.figureSpec = Figure()
        self.figureSpecCanvas = FigureCanvas(self.figureSpec)
        self.specLayout.addWidget(self.figureSpecCanvas)

        self.figureFig = Figure()
        self.figureFig.set_figheight(2.5)
        self.figureFigCanvas = FigureCanvas(self.figureFig)
        self.figLayout.addWidget(self.figureFigCanvas)

    def populateComboBoxes(self):
        self.windowComboBox.addItem('boxcar')
        self.windowComboBox.addItem('triang')
        self.windowComboBox.addItem('blackman')
        self.windowComboBox.addItem('hamming')
        self.windowComboBox.addItem('hann')
        self.windowComboBox.addItem('bartlett')
        self.windowComboBox.addItem('flattop')
        self.windowComboBox.addItem('parzen')
        self.windowComboBox.addItem('nuttall')
        self.windowComboBox.addItem('taylor')
        self.windowComboBox.setCurrentIndex(0)

        self.nfftComboBox.addItem('256', ['128', '250'])
        self.nfftComboBox.addItem('512', ['128', '256', '500'])
        self.nfftComboBox.addItem('1024', ['128', '256', '512', '1000'])
        self.nfftComboBox.addItem('2048', ['128', '256', '512', '1024', '2000'])
        self.nfftComboBox.addItem('4096', ['128', '256', '512', '1024', '2048', '4000'])
        self.nfftComboBox.setCurrentIndex(2)

        self.noverlapComboBox.addItem('256')
        self.noverlapComboBox.addItem('512')
        self.noverlapComboBox.addItem('1000')
        self.noverlapComboBox.setCurrentIndex(0)

        self.scaleComboBox.addItem('linear')
        self.scaleComboBox.addItem('symlog')
        self.scaleComboBox.setCurrentIndex(0)

        self.minFreqComboBox.addItem('0 [Hz]')
        self.minFreqComboBox.addItem('10 [Hz]')
        self.minFreqComboBox.addItem('20 [Hz]')
        self.minFreqComboBox.addItem('100 [Hz]')
        self.minFreqComboBox.setCurrentIndex(0)

        self.maxFreqComboBox.addItem('Auto')
        self.maxFreqComboBox.addItem('20 [Hz]')
        self.maxFreqComboBox.addItem('240 [Hz]')
        self.maxFreqComboBox.addItem('10000 [Hz]')
        self.maxFreqComboBox.addItem('20000 [Hz]')
        self.maxFreqComboBox.addItem('40000 [Hz]')
        self.maxFreqComboBox.setCurrentIndex(0)

    def clicker(self, index):
        self.noverlapComboBox.clear()
        self.noverlapComboBox.addItems(self.nfftComboBox.itemData(index))
        self.noverlapComboBox.setCurrentIndex(self.nfftComboBox.currentIndex())
        self.activateComboBoxes()

    def activateComboBoxes(self):
        if os.path.exists(self.filePath):
            self.plotSpectrogram(self.f)

    def triggeredViridis(self):
        self.actionInferno.setChecked(False)
        self.actionMagma.setChecked(False)
        self.actionRdBu.setChecked(False)

        self.colorMap = 'viridis'
        if self.filePath!='':
            self.plotSpectrogram(self.f)

    def triggeredInferno(self):
        self.actionViridis.setChecked(False)
        self.actionMagma.setChecked(False)
        self.actionRdBu.setChecked(False)

        self.colorMap = 'inferno'
        if self.filePath!='':
            self.plotSpectrogram(self.f)

    def triggeredMagma(self):
        self.actionViridis.setChecked(False)
        self.actionInferno.setChecked(False)
        self.actionRdBu.setChecked(False)

        self.colorMap = 'magma'
        if self.filePath!='':
            self.plotSpectrogram(self.f)

    def triggeredRdBu(self):
        self.actionViridis.setChecked(False)
        self.actionInferno.setChecked(False)
        self.actionMagma.setChecked(False)

        self.colorMap = 'RdBu'
        if self.filePath!='':
            self.plotSpectrogram(self.f)

    def triggeredOrange(self):
        self.actionBlack.setChecked(False)
        self.actionBlue.setChecked(False)
        self.actionRed.setChecked(False)

        self.color = 'orange'
        self.plotFigure()

    def triggeredBlack(self):
        self.actionOrange.setChecked(False)
        self.actionBlue.setChecked(False)
        self.actionRed.setChecked(False)

        self.color = 'black'
        self.plotFigure()

    def triggeredBlue(self):
        self.actionOrange.setChecked(False)
        self.actionBlack.setChecked(False)
        self.actionRed.setChecked(False)

        self.color = 'blue'
        self.plotFigure()

    def triggeredRed(self):
        self.actionOrange.setChecked(False)
        self.actionBlack.setChecked(False)
        self.actionBlue.setChecked(False)

        self.color = 'red'
        self.plotFigure()

    def triggeredBroad(self):
        self.actionAccurate.setChecked(False)

    def triggeredAccurate(self):
        self.actionBroad.setChecked(False)

    def triggeredRemoveSpan(self):
        if self.filePath!='':
            self.f = list(wavfile.read(self.filePath))
            self.plotFigure()
            self.plotSpectrogram(self.f)

    def getDirectory(self):
        chosenPath = str(QFileDialog.getOpenFileName(cpsMainWindow, caption="Select .wav file", filter='Audio (*.wav)')[0])

        if chosenPath!="":
            self.textPath.setText(chosenPath)
            self.filePath = chosenPath

            self.f = list(wavfile.read(self.filePath))
            self.plotFigure()
            self.plotSpectrogram(self.f)

    def runRecord(self):
        cpsMainWindow.hide()
        record = QDialog()
        uiRecord = recordWindow(record)
        uiRecord.setupUiRecord(record)
        record.show()
        record.exec_()
        if uiRecord.stringPath != '':
            temp = uiRecord.stringPath + '/' + str(uiRecord.filenameInput.text()) + '.wav'
            if os.path.exists(temp):
                self.filePath = uiRecord.stringPath + '/' + str(uiRecord.filenameInput.text()) + '.wav'
                self.textPath.setText(self.filePath)
                self.f = list(wavfile.read(self.filePath))
                self.plotSpectrogram(self.f)
                self.plotFigure()

        cpsMainWindow.show()

    def plotSpectrogram(self, f, startTime = 0):
        if self.filePath != '':
            samplingFrequency, signalData = f
            self.figureSpec.clear() 

            # Plot the signal read from wav file

            ax = self.figureSpec.add_subplot(111)

            nfft = int(self.nfftComboBox.currentText())
            nover = int(self.noverlapComboBox.currentText())

            if self.windowComboBox.currentText() == 'boxcar':
                win=signal.get_window('boxcar', len(signalData))
            elif self.windowComboBox.currentText() == 'triang':
                win=signal.get_window('triang', len(signalData))
            elif self.windowComboBox.currentText() == 'blackman':
                win=signal.get_window('blackman', len(signalData))
            elif self.windowComboBox.currentText() == 'hamming':
                win=signal.get_window('hamming', len(signalData))
            elif self.windowComboBox.currentText() == 'hann':
                win=signal.get_window('hann', len(signalData))
            elif self.windowComboBox.currentText() == 'bartlett':
                win=signal.get_window('bartlett', len(signalData))
            elif self.windowComboBox.currentText() == 'flattop':
                win=signal.get_window('flattop', len(signalData))
            elif self.windowComboBox.currentText() == 'parzen':
                win=signal.get_window('parzen', len(signalData))
            elif self.windowComboBox.currentText() == 'nuttall':
                win=signal.get_window('nuttall', len(signalData))
            elif self.windowComboBox.currentText() == 'taylor':
                win=signal.get_window('taylor', len(signalData))

            signalData = multiply(signalData, win)

            ax.specgram(signalData, NFFT=nfft, noverlap=nover, Fs=samplingFrequency, cmap=self.colorMap)

            ax.set_yscale(self.scaleComboBox.currentText())#linear or symlog
            if self.maxFreqComboBox.currentText()!='Auto':
                ax.set_ylim(0,int(self.maxFreqComboBox.currentText().split(' ', 1)[0]))
            ax.set_ylim(int(self.minFreqComboBox.currentText().split(' ', 1)[0]),)
            
            ax.set_title('Spectrogram', fontsize=12)
            ax.set_xlabel('Time [s]', fontsize=8)
            ax.set_ylabel('Frequency [Hz]', fontsize=8)
            ax.tick_params(labelsize=7)

            self.figureSpec.tight_layout(pad=0.3)

            self.figureSpecCanvas.draw()

    def spanSelected(self, startFrame, endFrame):
        signalData = self.f[1]

        chosenData = signalData[int(startFrame):int(endFrame)]

        if self.actionAccurate.isChecked():
            self.f[1] = chosenData
            self.plotFigure()
            tempF=self.f
        else:
            tempF=self.f.copy()
            tempF[1] = chosenData

        self.plotSpectrogram(tempF)

    def plotFigure(self):
        if self.filePath != '':
            rate, data = self.f
            
            if len(data.shape) == 1:
                channel1 = data[:]
                channel2 = None
            else:
                channel1 = data[:, 0]
                channel2 = data[:, 1]
            
            self.figureFig.clear() 
            axes = self.figureFig.add_subplot(111)

            n_ticks = 8
            max_time = len(channel1) / rate

            x_ticks = [len(channel1) * i / (n_ticks - 1) for i in range(n_ticks)]
            x_ticklabels = [f'{max_time * i / (n_ticks - 1):.2f}s' for i in range(n_ticks)]

            axes.plot(channel1, color = self.color)
 
            axes.set_title('Select span below', fontsize=10)
            axes.set_xticks(x_ticks)
            axes.set_xticklabels(x_ticklabels, fontsize=7)
            axes.set_yticks([0])
            axes.set_yticklabels(['y=0'], fontsize=7)
            axes.set_xlim([0,max(x_ticks)])
            axes.axhline(y=0, color = self.color, linewidth=1, linestyle = '-')

            self.figureFig.tight_layout(pad=0.1)
            
            self.figureFigCanvas.draw()

            self.span = SpanSelector(
                axes,
                self.spanSelected,
                "horizontal",
                minspan=1000,
                useblit=True,
                span_stays=True,
                rectprops=dict(alpha=0.3, facecolor="red"),
            )

if __name__ == "__main__":

    app = QApplication(sys.argv)
    cpsMainWindow = QMainWindow()
    ui = Ui_cpsApp()
    ui.setupUiApp(cpsMainWindow)
    cpsMainWindow.show()
    sys.exit(app.exec_())