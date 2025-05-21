import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
// import Qt.labs.platform
import QtQuick.Dialogs

import Modules
import Controls

WindowDialog {
    id: root
    width: 576
    standardButtons: DialogButtons.ok | DialogButtons.cancel
    states: [
        State {
            name: "installing"
            PropertyChanges { target: root; title: qsTr("Installing app") }
        },
        State {
            name: "adding"
            PropertyChanges { target: root; title: qsTr("Adding app") }
        }
    ]

    property var wineList: []
    property alias appName: textFieldAppName.text
    property alias appExe: textFieldExeName.text
    property alias wine: comboBoxWine.currentText
    property alias winVer: comboBoxWinVer.currentText
    property alias winBit: comboBoxWinBit.currentText

    function accept() {
        if (appName.length === 0) {
            errorDialog.text = qsTr("The program name cannot be empty.")
            errorDialog.show()
            return
        }
        if (appExe.length === 0) {
            errorDialog.text = qsTr("The file path cannot be empty.")
            errorDialog.show()
            return
        }
        accepted()
        close()
    }

    onVisibleChanged: {
        if (visible) {
            appName = ""
            appExe = ""
        }
    }
    onAccepted: {
        let app_data = {
            "appName": appName,
            "appExe": appExe,
            "winVer": winVer,
            "winBit": winBit,
            "wine": wine
        }
        AppEngine.addApplication(app_data)
    }

    content: GridLayout {
        columns: 3
        anchors.fill: parent
        anchors.margins: 10
        anchors.bottomMargin: 0

        Label { text: qsTr("Enter the name of the program:") }
        TextField {
            id: textFieldAppName
            Layout.fillWidth: true
            Layout.columnSpan: 2
        }

        Label { text: qsTr(`Select the ${ root.state === "installing" ? "installation" : "executable" } file:`) }
        RowLayout {
            Layout.columnSpan: 2
            TextField {
                id: textFieldExeName
                Layout.fillWidth: true
            }
            ImageButton {
                Layout.preferredWidth: implicitHeight
                icon.source: "qrc:/img/open-folder-64.png"
                onClicked: {
                    fileDialog.open()
                }
                 FileDialog {
                    id: fileDialog
                    title: qsTr(`Select the ${ root.state === "installing" ? "installation" : "executable" } file`)
                    onAccepted: {
                        textFieldExeName.text = selectedFile.toString().replace("file://", "");
                    }
                }
            }
        }

        Label { text: "Wine" }
        ComboBox {
            id: comboBoxWine
            Layout.fillWidth: true
            Layout.columnSpan: 2
            model: root.wineList
        }

        Label { text: qsTr("Installer preset") }
        ComboBox {
            id: comboBoxWinVer
            Layout.fillWidth: true
            model: ["Windows XP", "Windows 7", "Windows 8", "Windows 8.1", "Windows 10"]
            currentIndex: 4     // по замовчуванню win10
        }
        ComboBox {
            id: comboBoxWinBit
            Layout.fillWidth: true
            model: ["32 bit", "64 bit"]
            currentIndex: 1     // по замовчуванню 64bit
        }
    }
}
