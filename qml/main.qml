import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import Modules
import Controls

ApplicationWindow {
    id: appWindow
    visible: true
    minimumWidth: 640
    minimumHeight: 480
    title: qApp.applicationName + " " + qApp.applicationVersion

    function log(text) {
        labelLog.color = Colors.info
        labelLog.text = text;
        AppEngine.onMessage(text)
        timerLabelLog.running = true;
    }

    function error(text) {
        labelLog.color = Colors.error
        labelLog.text = text;
        AppEngine.onError(text)
        timerLabelLog.running = true;
    }

    Connections {
        target: AppEngine

        function onUpdateModelSignal(installedApps) {
            appsModel.clear();
            for (let app of installedApps) {
                appsModel.append({ "name": app.name, "icon": app.icon, "running": false });
            }
        }

        function onError(errorText) {
            error(errorText);
        }

        function onMessage(messageText) {
            log(messageText)
        }

        function onGetedWineList(wineMap) {
            dialogManageWine.wineMap = wineMap
        }

        function onWineStatusChanged() {
            AppEngine.getWineList()
        }

        function onRunningAppsChanged(appsList) {
            for (var i = 0; i < appsModel.count; ++i) {
                var item = appsModel.get(i)
                appsModel.set(i, { "name": item.name, "icon": item.icon, "running": appsList.includes(item.name) })
            }
        }
    }

    onClosing: (close) => {
        close.accepted = !AppEngine.hasRunningApps()
        if (!close.accepted) {
            errorDialog.text = qsTr("You cannot exit because you have processes running.")
            errorDialog.show()
            error(errorDialog.text)
        }
    }

    DialogConfig { id: dialogConfig }
    DialogInstallingAdding { id: dialogInstallingAdding }
    ErrorDialog { id: errorDialog }
    DialogManageWine { id: dialogManageWine }

    background: Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            GradientStop { position: 0.0; color: Colors.backgroundGradientStart }
            GradientStop { position: 1.0; color: Colors.backgroundGradientEnd }
        }
    }
    menuBar: MenuBar {
        Menu {
            id: menuFile
            title: qsTr("&File")
            Action {
                id: actionInstallApplications
                text: "Install application"
                shortcut: "Ctrl+I"
                icon.source: "qrc:/img/install-64.png"
                onTriggered: {
                    log("Installing application...");
                    dialogInstallingAdding.state = "installing";
                    dialogInstallingAdding.wineList = AppEngine.getInstalledWines();
                    dialogInstallingAdding.show();
                }
            }
            Action {
                id: actionAddApplications
                text: "Add application"
                shortcut: "Ctrl+A"
                icon.source: "qrc:/img/add-64.png"
                onTriggered: {
                    log("Adding application...");
                    dialogInstallingAdding.state = "adding";
                    dialogInstallingAdding.wineList = AppEngine.getInstalledWines();
                    dialogInstallingAdding.show();
                }
            }
            Action {
                id: actionQuit
                text: qsTr("Quit")
                shortcut: "Ctrl+Q"
                icon.source: "qrc:/img/exit-64.png"
                onTriggered: {
                    log("Quit...")
                    appWindow.close();
                }
            }
        }
        Menu {
            id: menuOptions
            title: qsTr("&Options")
            Action {
                id: actionManageWine
                text: qsTr("Manage Wine")
                onTriggered: {
                    log("Managing Wine...")
                    AppEngine.getWineList()
                    dialogManageWine.visible = true
                }

            }
            Action {
                id: actionScanApplications
                text: qsTr("Scan for installed applications")
                onTriggered: {
                    log("Scanning for applications...");
                    AppEngine.scanApplications();
                }
            }
        }
        Menu {
            id: menuSettings
            title: qsTr("&Settings")
            enabled: false
            Menu {
                id: menuLanguage
                title: qsTr("Language")
                Action {
                    id: actionEnglish
                    text: "English"
                    checkable: true
                }
                Action {
                    id: actionUkrainian
                    text: "Українська"
                    checkable: true
                }
            }
        }
    }

    footer: Rectangle {
        color: Colors.panelBackground
        height: labelLog.implicitHeight + 1
        Rectangle {
            color: Colors.borderColor
            width: parent.width
            height: 1
            anchors.top: parent.top
        }
        Label {
            id: labelLog
            anchors.bottom: parent.bottom
            anchors.left: parent.left
            anchors.right: parent.right
            padding: 5
            Timer {
                id: timerLabelLog
                interval: 7000
                running: false
                onTriggered: {
                    labelLog.text = "";
                }
            }
        }
    }

// Content
    Column {
        anchors.fill: parent
        spacing: 10
        padding: 10
        ListView {
            id:appListView
            width: parent.width
            height: parent.height
            clip: true
            model: ListModel { id: appsModel }
            ScrollBar.vertical: ScrollBar { policy: ScrollBar.AlwaysOn }
            delegate: Item {
                id: delegateAppModelList
                width: appListView.width - 20
                height: 40

                property bool hovered: false

                Rectangle {
                    radius: 3
                    anchors.fill: parent
                    color: delegateAppModelList.hovered ||
                            (appsBttContextMenu.hovered && appsBttContextMenu.appName === model.name) ||
                            (appsContextMenu.hovered && appsContextMenu.appName === model.name) ? Colors.selectionBackground : "transparent"
                    RowLayout {
                        anchors.fill: parent
                        anchors.margins: 4
                        spacing: 6
                        Rectangle {
                            width: 32
                            height: 32
                            radius: 6
                            color: Colors.textPrimary
                            Image {
                                anchors.fill: parent
                                source: `file:/${icon}`
                            }
                        }
                        Text {
                            text: name
                            font.pixelSize: 16
                            Layout.fillWidth: true
                            color: delegateAppModelList.hovered ? Colors.selectionText : Colors.textPrimary
                            font.bold: delegateAppModelList.hovered
                        }
                        ImageButton {
                            width: 32
                            height: 32
                            icon.source: model.running ? "qrc:/img/stop-64.png" : "qrc:/img/play-64.png"
                            onClicked: {
                                if (model.running) {
                                    AppEngine.terminateApp(model.name)
                                }
                                else {
                                    AppEngine.runApp(model.name)
                                }
                            }
                        }
                        ImageButton {
                            width: 32
                            height: 32
                            icon.source: "qrc:/img/settings-64.png"
                            enabled: !model.running
                            onClicked: {
                                dialogConfig.appName = model.name
                                dialogConfig.appSettings = AppEngine.getSettings(model.name)
                                dialogConfig.installedWines = AppEngine.getInstalledWines()
                                dialogConfig.show()
                            }
                        }
                        ImageButton {
                            width: 32
                            height: 32
                            icon.source: "qrc:/img/menu-64.png"
                            onClicked: {
                                appsBttContextMenu.appName = model.name
                                appsBttContextMenu.popup()
                            }
                        }
                    }
                    MouseArea {
                        anchors.fill: parent
                        hoverEnabled: true
                        acceptedButtons: Qt.RightButton
                        onClicked: (mouseEvent) => {
                            if (mouseEvent.button === Qt.RightButton) {
                                appsContextMenu.x = mouseEvent.x
                                appsContextMenu.y = mouseEvent.y
                                appsContextMenu.appName = model.name
                                appsContextMenu.popup()
                            }
                        }
                    }
                    HoverHandler {
                        acceptedDevices: PointerDevice.AllDevices
                        onHoveredChanged: { delegateAppModelList.hovered = hovered }
                    }
                }
            }
        }
    }
// end content

    Menu {
        id: appsBttContextMenu

        property string appName
        property bool appRunning

        onVisibleChanged: {
            if (visible)
                appRunning = AppEngine.isAppRunning(appName)
        }

        Action {
            text: qsTr("Terminate")
            onTriggered: { AppEngine.terminateApp(appsBttContextMenu.appName) }
            enabled: appsBttContextMenu.appRunning
        }
        Action {
            text: qsTr("Delete")
            onTriggered: { AppEngine.deleteApp(appsBttContextMenu.appName) }
            enabled: !appsBttContextMenu.appRunning
        }
        MenuSeparator {}
        Action {
            text: qsTr("Run winecfg")
            onTriggered: { AppEngine.runWinecfg(appsBttContextMenu.appName) }
            enabled: !appsBttContextMenu.appRunning
        }
        Action {
            text: qsTr("Run winetricks")
            onTriggered: { AppEngine.runWinetricks(appsBttContextMenu.appName) }
            enabled: !appsBttContextMenu.appRunning
        }
    }

    Menu {
        id: appsContextMenu

        property string appName
        property bool appRunning

        onVisibleChanged: {
            if (visible)
                appRunning = AppEngine.isAppRunning(appName)
        }

        Action {
            text: qsTr("Run")
            onTriggered: { AppEngine.runApp(appsContextMenu.appName) }
            enabled: !appsContextMenu.appRunning
        }
        Action {
            text: qsTr("Terminate")
            onTriggered: { AppEngine.terminateApp(appsBttContextMenu.appName) }
            enabled: appsContextMenu.appRunning
        }
        Action {
            text: qsTr("Delete")
            onTriggered: { AppEngine.deleteApp(appsContextMenu.appName) }
            enabled: !appsContextMenu.appRunning
        }
        Action {
            text: qsTr("Configure")
            onTriggered: {
                dialogConfig.appName = appsContextMenu.appName
                dialogConfig.appSettings = AppEngine.getSettings(appsContextMenu.appName)
                dialogConfig.installedWines = AppEngine.getInstalledWines()
                dialogConfig.show()
            }
            enabled: !appsContextMenu.appRunning
        }
        MenuSeparator {}
        Action {
            text: qsTr("Run winecfg")
            onTriggered: { AppEngine.runWinecfg(appsContextMenu.appName) }
            enabled: !appsContextMenu.appRunning
        }
        Action {
            text: qsTr("Run winetricks")
            onTriggered: { AppEngine.runWinetricks(appsContextMenu.appName) }
            enabled: !appsContextMenu.appRunning
        }
    }
}
