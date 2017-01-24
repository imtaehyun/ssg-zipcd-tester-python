import sys
import logging

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5 import uic

from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
import selenium.webdriver.support.expected_conditions as EC
import selenium.webdriver.support.ui as ui

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Signal:
    def __init__(self):
        self.__subscribers = []

    def emit(self, *args, **kwargs):
        for subs in self.__subscribers:
            subs(*args, **kwargs)

    def connect(self, func):
        self.__subscribers.append(func)

    def disconnect(self, func):
        try:
            self.__subscribers.remove(func)
        except ValueError:
            print('Warning: function %s not removed '
                  'from signal %s' % (func, self))


# signal = Signal()
# signal_end = Signal()


class MyWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.view = uic.loadUi('zipcd_tester_ui.ui', self)
        self.output_browser = self.view.browser_test_result

    @pyqtSlot()
    def start_test(self):
        # self.view.btn_test_start.setEnabled(False)

        try:
            selected_zone = self.view.select_zone.currentText()
            input_text = self.view.text_test_input.toPlainText()

            zipcd_tester = ZipcdTester(selected_zone, input_text)
            # signal.connect(self.update_text_browser)
            # signal_end.connect(self.end_test)
            zipcd_tester.start()

        except Exception as e:
            logger.exception(e, exc_info=True)

    def update_text_browser(self, data):
        self.output_browser.append(data)
        # self.output_browser.moveCursor(QTextCursor.End)

    def end_test(self):
        self.view.btn_test_start.setEnabled(True)
        QMessageBox.about(self, "테스트 완료", "테스트 완료")


class ZipcdTester(QThread):

    def __init__(self, zone, input_text):
        QThread.__init__(self)
        self.input_text = input_text

        self.driver = webdriver.PhantomJS()
        self.driver.set_window_size(500, 700)
        self.test_url = 'https://member.ssg.com/addr/popup/zipcd.ssg'
        if zone != 'prod':
            self.test_url = 'http://' + zone + '-member.ssg.com/addr/popup/zipcd.ssg'

    def __del__(self):
        self.wait()

    def is_visible(self, locator, timeout=2):
        """return True if element is visible within 2 seconds, otherwise False"""
        try:
            ui.WebDriverWait(self.driver, timeout).until(EC.visibility_of_element_located((By.CSS_SELECTOR, locator)))
            return True
        except TimeoutException:
            return False

    def analyze_param(self, addr_str):
        try:
            addr = addr_str.split(' ')
            sdNm = addr[0]
            sggNm = addr[1]

            roadNmAddr = ''

            for idx, str in enumerate(addr):
                # print(idx, str)
                if idx < 2:
                    continue

                if str.endswith('읍') or str.endswith('면') or str.endswith('동'):
                    continue

                if str.endswith('구'):
                    sggNm += ' ' + str
                    continue

                roadNmAddr += str + ' '

            # print(sdNm, sggNm, roadNmAddr)
            return sdNm, sggNm, roadNmAddr

        except Exception as e:
            logger.exception(e)

    def test(self, sdNm, sggNm, roadNmAddr):
        try:
            self.driver.get(self.test_url)

            Select(self.driver.find_element_by_css_selector('select[name="sdNm"]')).select_by_visible_text(sdNm)
            Select(self.driver.find_element_by_css_selector('select[name="sggNm"]')).select_by_visible_text(sggNm)
            self.driver.find_element_by_css_selector('#roadNmAddrQuery').clear()
            self.driver.find_element_by_css_selector('#roadNmAddrQuery').send_keys(roadNmAddr)
            self.driver.find_element_by_css_selector('#roadNmAddrQuery').send_keys(Keys.ENTER)
            self.is_visible('#address_street div.section.searchResult')

            result = self.driver.find_element_by_css_selector(
                '#address_street div.section.searchResult table table tbody').text.replace('\n', ' ')
            logger.info("output: %s", result)
            # signal.emit("output: {}".format(result))

        except Exception as e:
            result = ''
            logger.info("output: %s", result)
            # signal.emit("output: {}".format(result))

    def run(self):
        try:
            for addr in self.input_text.split('\n'):
                if addr:
                    sdNm, sggNm, roadNmAddr = self.analyze_param(addr)
                    logger.info("input: %s, %s, %s", sdNm, sggNm, roadNmAddr)
                    # signal.emit("input: {}, {}, {}".format(sdNm, sggNm, roadNmAddr))

                    self.test(sdNm, sggNm, roadNmAddr)
                    self.sleep(2)

            # signal_end.emit()
        except Exception as e:
            logger.exception(e, exc_info=True)


try:

    app = QApplication(sys.argv)
    myWindow = MyWindow()
    myWindow.show()
    app.exec_()

except Exception as e:
    logger.exception(e, exc_info=True)