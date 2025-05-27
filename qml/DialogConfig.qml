import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
// import Qt.labs.platform
import QtQuick.Dialogs

import Modules
import Controls

WindowDialog {
    id: root
    standardButtons: DialogButtons.ok | DialogButtons.cancel
    width: 576
    title: `${appName} ${qsTr("config")}`

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
    property var installedWines

    onVisibleChanged: {
        if (visible) {
            textFieldWinePrefix.text = appSettings["wine_prefix_path"]
            textFieldExecutable.text = appSettings["exe_path"]
            textFieldIcon.text = appSettings["icon_path"]

            let wineVerIdx = comboBoxWineVersion.find(appSettings["wine_version"])
            if (wineVerIdx !== -1)
                comboBoxWineVersion.currentIndex = wineVerIdx
            // let winePrArc = comboBoxPrefixArchitecture.find(appSettings["wine_bit"])
            // if (winePrArc !== -1)
            //     comboBoxPrefixArchitecture.currentIndex = winePrArc

            if (appSettings["settings_json"]) {
                let settings_json = JSON.parse(appSettings["settings_json"])
                if ("env" in settings_json)
                    textFieldEnv.text = settings_json.env
            }
            else {
                textFieldEnv.text = ""
            }
        }
    }
    onAccepted: {
        if (appSettings["name"] === "") appSettings["name"] = appName
        appSettings["wine_prefix_path"] = textFieldWinePrefix.text
        appSettings["exe_path"] = textFieldExecutable.text
        appSettings["wine_version"] = comboBoxWineVersion.currentText
        // appSettings["wine_bit"] = comboBoxPrefixArchitecture.currentText
        appSettings["wine_path"] = AppEngine.getWinePath(appSettings["wine_version"], appSettings["wine_bit"])
        appSettings["icon_path"] = textFieldIcon.text
        let settings_json = { env: textFieldEnv.text }
        appSettings["settings_json"] = JSON.stringify(settings_json)
        AppEngine.saveSettings(appSettings)
    }

    content: GridLayout {
        columns: 3
        anchors.fill: parent
        anchors.margins: 10
        anchors.bottomMargin: 0

        Label { text: qsTr("Wine prefix") }
        TextField {
            id: textFieldWinePrefix
            Layout.fillWidth: true
        }
        ImageButton {
            Layout.preferredWidth: implicitHeight
            icon.source: "qrc:/img/open-folder-64.png"
            onClicked: {
                folderDialogWinePrefix.open()
            }
            FolderDialog {
                id: folderDialogWinePrefix
                currentFolder: `file://${textFieldWinePrefix.text}`
                title: qsTr("Select Wine prefix folder")
                onAccepted: {
                    textFieldWinePrefix.text = currentFolder.toString().replace("file://", "");
                }
            }
        }

        Label { text: qsTr("Executable") }
        TextField {
            id: textFieldExecutable
            Layout.fillWidth: true
        }
        ImageButton {
            Layout.preferredWidth: implicitHeight
            icon.source: "qrc:/img/file-64.png"
            onClicked: {
                fileDialogConfigExe.currentFile = `file://${textFieldExecutable.text}`
                fileDialogConfigExe.open()
            }
            FileDialog {
                id: fileDialogConfigExe
                title: qsTr("Select executable file")
                onAccepted: {
                    textFieldExecutable.text = currentFile.toString().replace("file://", "");
                }
            }
        }

        Label { text: qsTr("Icon") }
        TextField {
            id: textFieldIcon
            Layout.fillWidth: true
        }
        ImageButton {
            Layout.preferredWidth: implicitHeight
            icon.source: "qrc:/img/file-64.png"
            onClicked: {
                fileDialogConfigIco.currentFile = `file://${textFieldIcon.text}`
                fileDialogConfigIco.open()
            }
            FileDialog {
                id: fileDialogConfigIco
                title: qsTr("Select icon file")
                onAccepted: {
                    textFieldIcon.text = currentFile.toString().replace("file://", "");
                }
            }
        }

        Label { text: qsTr("Wine version") }
        ComboBox {
            id: comboBoxWineVersion
            model: root.installedWines
            Layout.fillWidth: true
            Layout.columnSpan: 2
        }

        // Label { text: qsTr("Prefix architecture") }
        // ComboBox {
        //     id: comboBoxPrefixArchitecture
        //     Layout.fillWidth: true
        //     Layout.columnSpan: 2
        //     model: ["32 bit", "64 bit"]
        // }

        Label { text: qsTr("Environment variables") }
        TextField {
            id: textFieldEnv
            Layout.fillWidth: true
            Layout.columnSpan: 2
        }
    }
}
