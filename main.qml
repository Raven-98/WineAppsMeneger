import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs

ApplicationWindow {
    id: appWindow
    visible: true
    minimumWidth: 640
    minimumHeight: 480
    title: qApp.applicationName + " " + qApp.applicationVersion

    // font.pixelSize: 12

    onVisibleChanged: {
        AppEngine.test()
    }

    menuBar: MenuBar {
        id: menuBar

        Menu {
            id: menuFile
            title: qsTr("&File")

            Action {
                id: actionInstallApplications
                text: "Install application"
                shortcut: "Ctrl+I"
                onTriggered: {
                    log("Installing application...");
                    wineComboBoxI.model = AppEngine.getInstalledWines()
                    dialogInstalling.visible = true;
                }
            }

            Action {
                id: actionAddApplications
                text: "Add application"
                // shortcut: "Ctrl+I"
                // enabled: false
                onTriggered: {
                    log("Adding application...");
                    wineComboBoxA.model = AppEngine.getInstalledWines()
                    dialogAdding.visible = true;
                }
            }

            Action {
                id: actionQuit
                text: qsTr("Quit")
                shortcut: "Ctrl+Q"
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
        height: labelLog.implicitHeight + 1
        color: appWindow.color

        Rectangle {
            height: 1
            color: "#d3d3d3"
            anchors.top: parent.top
            anchors.left: parent.left
            anchors.right: parent.right
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

    Column {
        anchors.fill: parent
        spacing: 10
        padding: 10

        ListView {
            id:appListView
            width: parent.width
            height: parent.height
            clip: true

            model: appsModel

            ScrollBar.vertical: ScrollBar {
                policy: ScrollBar.AlwaysOn
            }

            delegate: Item {
                // width: parent.width - 20
                width: appListView.width - 20
                height: 50

                Rectangle {
                    id: rowBackground
                    color: appListViewMouseArea.containsMouse ? "#d3d3d3" : "transparent"
                    radius: 3
                    anchors.fill: parent

                    Row {
                        anchors.fill: parent
                        spacing: 5
                        padding: 5

                        Image {
                            source: icon
                            width: 32
                            height: 32
                            anchors.verticalCenter: parent.verticalCenter
                        }

                        Text {
                            text: name
                            font.pixelSize: 16
                            anchors.verticalCenter: parent.verticalCenter
                        }
                    }

                    MouseArea {
                        id: appListViewMouseArea
                        anchors.fill: parent
                        hoverEnabled: true
                        acceptedButtons: Qt.LeftButton | Qt.RightButton

                        onDoubleClicked: (mouseEvent) => {
                            if (mouseEvent.button === Qt.LeftButton)
                                AppEngine.runApp(model.name)
                        }

                        onClicked: (mouseEvent) => {
                            if (mouseEvent.button === Qt.RightButton) {
                                appsContextMenu.x = mouseEvent.x
                                appsContextMenu.y = mouseEvent.y
                                appsContextMenu.appName = model.name
                                appsContextMenu.popup()
                            }
                        }
                    }
                }
            }
        }
    }

    ListModel {
        id: appsModel
    }

    Menu {
        id: appsContextMenu

        property string appName

        MenuItem {
            text: qsTr("Run")

            onTriggered: {
                AppEngine.runApp(appsContextMenu.appName)
            }
        }

        MenuItem {
            text: qsTr("Delete")
            onTriggered: {
                AppEngine.deleteApp(appsContextMenu.appName)
            }
        }

        MenuItem {
            text: qsTr("Configure")
            onTriggered: {
                dialogConfig.appName = appsContextMenu.appName
                dialogConfig.appSettings = AppEngine.getSettings(appsContextMenu.appName)
                comboBoxWineVersion.model = AppEngine.getInstalledWines()
                dialogConfig.visible = true
            }
        }

        MenuItem {
            text: qsTr("Run winecfg")
            onTriggered: {
                AppEngine.runWinecng(appsContextMenu.appName)
            }
        }

        MenuItem {
            text: qsTr("Run winetricks")
            onTriggered: {
                AppEngine.runWinetricks(appsContextMenu.appName)
            }
        }
    }

    Dialog {
        id: dialogConfig
        implicitWidth: 576
        // implicitHeight: 200
        anchors.centerIn: parent
        modal: true
        standardButtons: Dialog.Ok | Dialog.Cancel

        property string appName
        property var appSettings: {
            "name": "",
            "wine_prefix_path": "",
            "wine_path": "",
            "wine_version": "",
            "wine_bit": "",
            "exe_path": "",
            "icon_path": "",
            "settings_json": ""
        }

        onVisibleChanged: {
            let wineVerIdx = comboBoxWineVersion.find(appSettings["wine_version"])
            if (wineVerIdx !== -1)
                comboBoxWineVersion.currentIndex = wineVerIdx
            let winePrArc = comboBoxPrefixArchitecture.find(appSettings["wine_bit"])
            if (winePrArc !== -1)
                comboBoxPrefixArchitecture.currentIndex = winePrArc
        }

        onAccepted: {
            if (appSettings["name"] === "") appSettings["name"] = appName
            appSettings["wine_prefix_path"] = textFieldWinePrefix.text
            appSettings["exe_path"] = textFieldExecutable.text
            appSettings["wine_version"] = comboBoxWineVersion.currentText
            appSettings["wine_bit"] = comboBoxPrefixArchitecture.currentText
            appSettings["wine_path"] = AppEngine.getWinePath(appSettings["wine_version"], appSettings["wine_bit"])            
            appSettings["icon_path"] = textFieldIcon.text
            AppEngine.saveSettings(appSettings)
        }

        GridLayout {
            columns: 3
            anchors.fill: parent
            Layout.margins: 10

            Label {
                text: qsTr("Wine prefix")
            }
            TextField {
                id: textFieldWinePrefix
                Layout.fillWidth: true
                text: dialogConfig.appSettings["wine_prefix_path"]
            }
            Button {
                Layout.preferredWidth: implicitHeight
                icon.name: "folder"
                onClicked: {
                    folderDialogWinePrefix.open()
                }

                FolderDialog {
                    id: folderDialogWinePrefix
                    currentFolder: `file://${textFieldWinePrefix.text}`
                    onAccepted: {
                        textFieldWinePrefix.text = selectedFolder.toString().replace("file://", "");
                    }
                }
            }

            Label {
                text: qsTr("Executable")
            }
            TextField {
                id: textFieldExecutable
                Layout.fillWidth: true
                text: dialogConfig.appSettings["exe_path"]
            }
            Button {
                Layout.preferredWidth: implicitHeight
                icon.name: "document-open"
                onClicked: {
                    fileDialogConfigExe.open()
                }

                FileDialog {
                    id: fileDialogConfigExe
                    currentFile: `file://${textFieldExecutable.text}`
                    onAccepted: {
                        textFieldExecutable.text = selectedFile.toString().replace("file://", "");
                    }
                }
            }

            Label { text: qsTr("Icon") }
            TextField {
                id: textFieldIcon
                Layout.fillWidth: true
                text: dialogConfig.appSettings["icon_path"]
            }
            Button {
                Layout.preferredWidth: implicitHeight
                icon.name: "document-open"
                onClicked: {
                    fileDialogConfigIco.open()
                }

                FileDialog {
                    id: fileDialogConfigIco
                    currentFile: `file://${textFieldIcon.text}`
                    onAccepted: {
                        textFieldIcon.text = selectedFile.toString().replace("file://", "");
                    }
                }
            }

            Label {
                text: qsTr("Wine version")
            }
            ComboBox {
                id: comboBoxWineVersion
                Layout.fillWidth: true
                Layout.columnSpan: 2
            }

            Label {
                text: qsTr("Prefix architecture")
            }
            ComboBox {
                id: comboBoxPrefixArchitecture
                Layout.fillWidth: true
                Layout.columnSpan: 2
                model: ["32 bit", "64 bit"]
            }
        }
    }

    Dialog {
        id: dialogInstalling
        anchors.centerIn: parent
        modal: true
        // standardButtons: Dialog.Ok | Dialog.Cancel

        GridLayout {
            columns: 3
            anchors.fill: parent
            Layout.margins: 10

            Label {
                text: qsTr("Enter the name of the program:")
            }

            TextField {
                id: textFieldAppNameI
                Layout.fillWidth: true
                Layout.columnSpan: 2
            }

            Label {
                text: qsTr("Select the installation file:")
            }

            RowLayout {
                Layout.columnSpan: 2

                TextField {
                    id: textFieldFileI
                    Layout.fillWidth: true
                }

                Button {
                    Layout.preferredWidth: implicitHeight
                    icon.name: "folder"

                    onClicked: {
                        fileDialogI.open()
                    }

                    FileDialog {
                        id: fileDialogI

                        onAccepted: {
                            textFieldFileI.text = selectedFile.toString().replace("file://", "");
                        }
                    }
                }
            }

            Label {
                text: "Wine"
            }

            ComboBox {
                id: wineComboBoxI
                Layout.fillWidth: true
                Layout.columnSpan: 2
            }

            Label {
                text: qsTr("Installer preset")
            }

            ComboBox {
                id: comboBoxWinVerI
                Layout.fillWidth: true
                model: ["Windows XP", "Windows 7", "Windows 8", "Windows 8.1", "Windows 10"]
                currentIndex: 4     // по замовчуванню win10
            }

            ComboBox {
                id: comboBoxWinBitI
                model: ["32 bit", "64 bit"]
                currentIndex: 1     // по замовчуванню 64bit
            }

            RowLayout {
                Layout.columnSpan: 3
                Layout.alignment: Qt.AlignRight

                Button {
                    id: buttonOkI
                    text: "Ok"
                    onClicked: {
                        if (textFieldAppNameI.text.length === 0) {
                            errorDialog.text = qsTr("The program name cannot be empty.");
                            errorDialog.visible = true;
                            return;
                        }
                        dialogInstalling.accept()
                    }
                }

                Button {
                    id: buttonCancelI
                    text: qsTr("Cancel")
                    onClicked: { dialogInstalling.reject() }
                }
            }
        }

        onAccepted: {
            let app_data = {
                "appName": textFieldAppNameI.displayText,
                "appExe": textFieldFileI.text,
                "winVer": comboBoxWinVerI.currentText,
                "winBit": comboBoxWinBitI.currentText,
                "wine": wineComboBoxI.currentText
            }
            AppEngine.installApplication(app_data);
        }
    }

    Dialog {
        id: dialogAdding
        anchors.centerIn: parent
        modal: true
        // standardButtons: Dialog.Ok | Dialog.Cancel

        GridLayout {
            columns: 3
            anchors.fill: parent
            Layout.margins: 10

            Label {
                text: qsTr("Enter the name of the program:")
            }

            TextField {
                id: textFieldAppNameA
                Layout.fillWidth: true
                Layout.columnSpan: 2
            }

            Label {
                text: qsTr("Select the executable file:")
            }

            RowLayout {
                Layout.columnSpan: 2

                TextField {
                    id: textFieldFileA
                    Layout.fillWidth: true
                }

                Button {
                    Layout.preferredWidth: implicitHeight
                    icon.name: "folder"

                    onClicked: {
                        fileDialogA.open()
                    }

                    FileDialog {
                        id: fileDialogA

                        onAccepted: {
                            textFieldFileA.text = selectedFile.toString().replace("file://", "");
                        }
                    }
                }
            }            

            Label {
                text: "Wine"
            }

            ComboBox {
                id: wineComboBoxA
                Layout.fillWidth: true
                Layout.columnSpan: 2
            }

            Label {
                text: qsTr("Installer preset")
            }

            ComboBox {
                id: comboBoxWinVerA
                Layout.fillWidth: true
                model: ["Windows XP", "Windows 7", "Windows 8", "Windows 8.1", "Windows 10"]
                currentIndex: 4     // по замовчуванню win10
            }

            ComboBox {
                id: comboBoxWinBitA
                model: ["32 bit", "64 bit"]
                currentIndex: 1     // по замовчуванню 64bit
            }

            RowLayout {
                Layout.columnSpan: 3
                Layout.alignment: Qt.AlignRight

                Button {
                    id: buttonOkA
                    text: "Ok"
                    onClicked: {
                        if (textFieldAppNameA.text.length === 0) {
                            errorDialog.text = qsTr("The program name cannot be empty.");
                            errorDialog.visible = true;
                            return;
                        }
                        if (textFieldFileA.text.length === 0) {
                            errorDialog.text = qsTr("The file path cannot be empty.");
                            errorDialog.visible = true;
                            return;
                        }
                        dialogAdding.accept()
                    }
                }

                Button {
                    id: buttonCancelA
                    text: qsTr("Cancel")
                    onClicked: { dialogAdding.reject() }
                }
            }
        }

        onAccepted: {
            let app_data = {
                "appName": textFieldAppNameA.displayText,
                "appExe": textFieldFileA.text,
                "winVer": comboBoxWinVerA.currentText,
                "winBit": comboBoxWinBitA.currentText,
                "wine": wineComboBoxA.currentText
            }
            AppEngine.addApplication(app_data);
        }
    }

    Dialog {
        id: dialogManageWine
        height: 300
        width: 400
        anchors.centerIn: parent
        modal: true
        standardButtons: Dialog.Ok

        property bool loading: true

        Column {
            anchors.fill: parent
            spacing: 10
            padding: 10

            ListView {
                id: wineListView
                width: parent.width
                height: parent.height - 20
                clip: true

                model: ListModel { id: wineListModel }

                ScrollBar.vertical: ScrollBar {
                    policy: ScrollBar.AlwaysOn
                }

                delegate: Item {
                    // width: parent.width - 20
                    width: wineListView.width - 20
                    height: Math.max(buttonWine.implicitHeight, wineRowText.implicitHeight) + 10

                    Rectangle {
                        id: rowWineBackground
                        color: !dialogManageWine.loading && (mouseAreaWine.containsMouse || buttonWine.hovered) ? "#d3d3d3" : "transparent"
                        radius: 3
                        anchors.fill: parent

                        MouseArea {
                            id: mouseAreaWine
                            anchors.fill: parent
                            hoverEnabled: true
                        }

                        Row {
                            anchors.fill: parent
                            spacing: 5
                            padding: 5

                            Text {
                                id: wineRowText
                                text: "Wine-" + model.name
                                anchors.verticalCenter: parent.verticalCenter
                                wrapMode: Text.Wrap
                                elide: Text.ElideRight
                                horizontalAlignment: Text.AlignLeft
                                // width: parent.width - buttonWine.width - parent.spacing - parent.padding * 2
                                width: parent.width - buttonWine.width - 15
                                // anchors.margins: 10
                            }

                            Button {
                                id: buttonWine
                                text: model.url === "system" ? qsTr("System") : !model.installed ? qsTr("Install") : qsTr("Uninstall")
                                enabled: model.url !== "system"

                                onClicked: {
                                    if (!model.installed)
                                        AppEngine.installWine(model.name, model.url)
                                    else
                                        AppEngine.uninstallWine(model.name)
                                    dialogManageWine.loading = true
                                }
                            }
                        }
                    }
                }
            }
        }

        Rectangle {
            id: wineLoadingOverlay
            anchors.fill: parent
            color: "#50000000"
            visible: dialogManageWine.loading
            z: 10

            BusyIndicator {
                anchors.centerIn: parent
                running: true
            }

            MouseArea {
                anchors.fill: parent
                enabled: true
            }

            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                anchors.top: parent.verticalCenter
                anchors.topMargin: 40
                text: qsTr("Loading...")
                color: "white"
                font.bold: true
            }
        }
    }

    MessageDialog {
        id: errorDialog
        title: "Error"
        buttons: MessageDialog.Ok
    }


    function log(text) {
        labelLog.color = "#000000";
        labelLog.text = text;
        console.log(text)
        timerLabelLog.running = true;
    }

    function error(text) {
        labelLog.color = "#ff0000";
        labelLog.text = text;
        console.log(text)
        timerLabelLog.running = true;
    }

    Connections {
        target: AppEngine

        function onUpdateModelSignal(installedApps) {
            appsModel.clear();
            for (let app of installedApps) {
                appsModel.append({ "name": app.name, "icon": app.icon });
            }
        }

        function onError(errorText) {
            error(errorText);
        }

        function onMessage(messageText) {
            log(messageText)
        }

        function onGetedWineList(wineMap) {
            wineListModel.clear()
            let wineList = Object.keys(wineMap).sort()
            wineList.sort((a, b) => {
                              let installedA = wineMap[a][1]
                              let installedB = wineMap[b][1]
                              if (installedA === installedB) {
                                  return a.localeCompare(b)
                              }
                              return installedA ? -1 : 1
                          })
            for (let wine of wineList) {
                wineListModel.append({"name": wine, "url": wineMap[wine][0], "installed": wineMap[wine][1]})
            }
            dialogManageWine.loading = false
        }

        function onWineStatusChanged() {
            AppEngine.getWineList()
        }
    }
}
