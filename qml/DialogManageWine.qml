import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import Modules
import Controls

WindowDialog {
    id: root
    height: 360
    width: 480

    property bool loading: true
    property var wineMap
    property var tabs
    property var tabsData: ({})

    onWineMapChanged: {
        let wineList = Object.keys(wineMap).sort()
        wineList.sort((a, b) => {
                          let installedA = wineMap[a][1]
                          let installedB = wineMap[b][1]
                          if (installedA === installedB) {
                              return b.localeCompare(a)
                          }
                          return installedA ? -1 : 1
                      })

        let tabsList = ["Installed"]
        if (!tabsData) tabsData = {}

        if (!tabsData["Installed"])
            tabsData["Installed"] = Qt.createQmlObject('import QtQuick; ListModel {}', root)
        else
            tabsData["Installed"].clear()


        for (let wine of wineList) {
            let wineTp = wine.split(" - ")[0]
            if (tabsList.indexOf(wineTp) === -1 && wineTp !== "system") {
                tabsList.push(wineTp)
                if (!tabsData[wineTp])
                    tabsData[wineTp] = Qt.createQmlObject('import QtQuick; ListModel {}', root)
                else
                    tabsData[wineTp].clear()
            }
        }
        root.tabs = tabsList

        for (let wine of wineList) {
            let wineS = wine.split(" - ")
            let wineTp = wineS[0]
            let wineNm = wineS[1]
            if (wineMap[wine][1]) {
                tabsData["Installed"].append({"name": wineNm, "url": wineMap[wine][0], "installed": wineMap[wine][1], "type": wineTp, "mod": true})
            }
            if (tabsList.indexOf(wineTp) !== -1) {
                tabsData[wineTp].append({"name": wineNm, "url": wineMap[wine][0], "installed": wineMap[wine][1], "type": wineTp, "mod": false})
            }
        }

        root.loading = false
    }

    customButtons: [
        Button {
            id: buttonUpdateWinesList
            text: qsTr("Update Wines list")
            enabled: !root.loading
            onClicked: {
                root.loading = true
                AppEngine.updateWineList()
            }
        }
    ]

    content: Item {
        anchors.fill: parent
        anchors.margins: 10
        anchors.bottomMargin: 0
        TabBar {
            id: tabBar
            width: parent.width
            anchors.top: parent.top
            Repeater {
                model: root.tabs
                TabButton {
                    text: modelData
                }
            }
        }
        Rectangle {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            anchors.top: tabBar.bottom
            color: "transparent"
            border.color: Colors.borderColor
            StackLayout {
                id: stackLayout
                anchors.topMargin: 6
                anchors.fill:parent
                currentIndex: tabBar.currentIndex
                Repeater {
                    model: root.tabs
                    ListView {
                        id: listView
                        width: parent.width
                        height: parent.height - 20
                        clip: true
                        model: root.tabsData[modelData]
                        ScrollBar.vertical: ScrollBar {
                            policy: ScrollBar.AlwaysOn
                        }
                        delegate: Rectangle {
                            property bool hovered: false

                            width: listView.width - 20
                            height: Math.max(button.implicitHeight, textWine.implicitHeight) + 10
                            color: !root.loading && hovered ? Colors.selectionBackground : "transparent"
                            Row {
                                anchors.fill: parent
                                spacing: 5
                                padding: 5
                                Text {
                                    id: textWine
                                    text: !model.mod || model.type === "system" ? model.name : `${model.name} (${model.type})`
                                    color: Colors.textPrimary
                                    font.pixelSize: Helper.fontPixelSize
                                    anchors.verticalCenter: parent.verticalCenter
                                    wrapMode: Text.Wrap
                                    elide: Text.ElideRight
                                    horizontalAlignment: Text.AlignLeft
                                    width: parent.width - button.width - 15
                                }
                                Button {
                                    id: button
                                    anchors.verticalCenter: parent.verticalCenter
                                    implicitHeight: 24
                                    text: model.type === "system" ? qsTr("System") : !model.installed ? qsTr("Install") : qsTr("Uninstall")
                                    enabled: model.type !== "system"
                                    onClicked: {
                                        if (!model.installed)
                                            AppEngine.installWine(`${model.type} - ${model.name}`, model.url)
                                        else
                                            AppEngine.uninstallWine(`${model.type} - ${model.name}`)
                                        root.loading = true
                                    }
                                }
                            }
                            HoverHandler {
                                acceptedDevices: PointerDevice.AllDevices
                                onHoveredChanged: {
                                    parent.hovered = hovered
                                    textWine.font.bold = hovered
                                }
                            }
                        }
                    }
                }
            }
        }
        Rectangle {
            anchors.fill: parent
            color: "#50000000"
            visible: root.loading
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
}
