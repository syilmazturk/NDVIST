# -*- coding: utf-8 -*-
"""
/***************************************************************************
 NDVIST
                                 A QGIS plugin
 The NDVIST plugin lets you create a point grid that includes NDVI values for Istanbul.
                              -------------------
        begin                : 2017-03-22
        git sha              : $Format:%H$
        copyright            : (C) 2017 by Serhat YILMAZTURK
        email                : serhat@yilmazturk.info
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
from PyQt4.QtCore import QSettings, QTranslator, qVersion, QCoreApplication
from PyQt4.QtGui import QAction, QIcon
# Initialize Qt resources from file resources.py
import resources
# Import the code for the dialog
from PyQt4.QtCore import pyqtSlot, QUrl, QVariant
from PyQt4.QtGui import QMessageBox
from PyQt4 import uic
from qgis.core import QgsVectorLayer, QgsField, QgsGeometry, QgsFeature, QgsPoint, QgsMapLayerRegistry
from qgis.utils import iface
from qgis.gui import QgsMessageBar
from numpy import arange
import itertools
import urllib2
import json
from ndvist_dialog import NDVISTDialog
import os.path


js_ne_lat = "$(ne_lat)"
js_ne_lng = "$(ne_lng)"
js_sw_lat = "$(sw_lat)"
js_sw_lng = "$(sw_lng)"


class NDVIST:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'NDVIST_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

        # Create the dialog (after translation) and keep reference
        self.dlg = NDVISTDialog()
        self.dlg.setFixedSize(396, 257)

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&NDVIST')
        # TODO: We are going to let the user set this up in a future iteration
        self.toolbar = self.iface.addToolBar(u'NDVIST')
        self.toolbar.setObjectName(u'NDVIST')

        self.populate_combobox()
        self.dlg.pushButton_aoi.clicked.connect(self.popup_show)
        self.dlg.pushButton_grid.clicked.connect(self.plot_grid)

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('NDVIST', message)


    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None):
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            self.toolbar.addAction(action)

        if add_to_menu:
            self.iface.addPluginToMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/NDVIST/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'The NDVIST plugin lets you create a point grid that includes NDVI values for Istanbul.'),
            callback=self.run,
            parent=self.iface.mainWindow())


    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&NDVIST'),
                action)
            self.iface.removeToolBarIcon(action)
        # remove the toolbar
        del self.toolbar

    def populate_combobox(self):
        global sentinel_dates
        sentinel_dates = {
            "February 8th, 2016": "20160208",
            "July 24th, 2016": "20160724"
        }

        date_list = []
        for date in sentinel_dates.keys():
            date_list.append(date)
        self.dlg.comboBox_date.addItems(date_list)

    def popup_show(self):
        @pyqtSlot()
        def close_popup():
            global ne_lat, ne_lng, sw_lat, sw_lng
            ne_lat = self.ui.webView_aoi.page().mainFrame().evaluateJavaScript(js_ne_lat)
            ne_lng = self.ui.webView_aoi.page().mainFrame().evaluateJavaScript(js_ne_lng)
            sw_lat = self.ui.webView_aoi.page().mainFrame().evaluateJavaScript(js_sw_lat)
            sw_lng = self.ui.webView_aoi.page().mainFrame().evaluateJavaScript(js_sw_lng)
            self.ui.close()

        self.ui = uic.loadUi(os.path.join(os.path.dirname(__file__), 'webView_gmap.ui'))
        self.ui.webView_aoi.load(QUrl('http://yilmazturk.info/ndvist/index.html'))
        self.ui.setWindowTitle('Define area of interest')
        self.ui.pushButton.clicked.connect(close_popup)
        self.ui.show()

    def plot_grid(self):
        point_interval = self.dlg.lineEdit_interval.text()
        latlist = list(arange(sw_lat['0'], ne_lat['0'], float(point_interval)))
        lnglist = list(arange(sw_lng['0'], ne_lng['0'], float(point_interval)))

        msgBox = QMessageBox()
        msgBox.setWindowTitle('Info')
        message = "%s points will be generated. Continue?" % str(len(list(itertools.product(latlist, lnglist))))
        msgBox.setText(message)
        msgBox.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        pop = msgBox.exec_()

        if pop == QMessageBox.Yes:
            url = "http://universal-syilmazturk.rhcloud.com/ndvist/aoicheck/%f/%f/%f/%f" % (sw_lng['0'], sw_lat['0'],
                                                                                            ne_lng['0'], ne_lat['0'])
            req = urllib2.Request(url, None)
            response = urllib2.urlopen(req)
            data = json.load(response)
            aoi_status = data[0]['status']
            if aoi_status == 'inAOI':
                layer_name = 'grid_'
                coord_pairs = []
                memory_layer = QgsVectorLayer("Point?crs=epsg:4326", layer_name, "memory")
                memory_layer.startEditing()
                provider = memory_layer.dataProvider()
                provider.addAttributes([QgsField("NDVI_VALUE", QVariant.Double),
                                        QgsField("DATE", QVariant.Double)])
                sentinel_date_full = self.dlg.comboBox_date.currentText()
                sentinel_date_id = sentinel_dates[sentinel_date_full]

                for i in itertools.product(latlist, lnglist):
                    url = "http://universal-syilmazturk.rhcloud.com/ndvist/ndvivalue/%f/%f/%s" % (i[1], i[0],
                                                                                                  sentinel_date_id)
                    req = urllib2.Request(url, None)
                    response = urllib2.urlopen(req)
                    data = json.load(response)

                    geometry = QgsGeometry.fromPoint(QgsPoint(i[1], i[0]))
                    feature = QgsFeature()
                    feature.setGeometry(geometry)
                    feature.setAttributes([data[0]['ndviValue'], sentinel_date_id])
                    coord_pairs.append(feature)

                memory_layer.dataProvider().addFeatures(coord_pairs)
                memory_layer.updateExtents()
                memory_layer.commitChanges()
                QgsMapLayerRegistry.instance().addMapLayer(memory_layer)
            else:
                iface.messageBar().pushMessage(u"Info: ", "out",
                                               level=QgsMessageBar.SUCCESS, duration=5)


    def run(self):
        """Run method that performs all the real work"""
        # show the dialog
        self.dlg.show()
        # Run the dialog event loop
        result = self.dlg.exec_()
        # See if OK was pressed
        if result:
            # Do something useful here - delete the line containing pass and
            # substitute with your code.
            pass
