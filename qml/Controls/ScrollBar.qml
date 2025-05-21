import QtQuick
import QtQuick.Controls.Basic

import Modules

ScrollBar {
    id: root
    contentItem: Rectangle {
        implicitWidth: root.interactive ? 6 : 2
        implicitHeight: root.interactive ? 6 : 2
        radius: width / 2
        color: root.pressed ? Colors.scrollbarHandleHover : Colors.scrollbarHandle
        border.color: Colors.borderColor
        opacity: root.policy === ScrollBar.AlwaysOn || (root.active && root.size < 1.0) ? 0.75 : 0
        // Animate the changes in opacity (default duration is 250 ms).
        Behavior on opacity {
            NumberAnimation {}
        }
    }
    background: Rectangle {
        color: Colors.scrollbarBackground
        opacity: root.policy === ScrollBar.AlwaysOn || (root.active && root.size < 1.0) ? 0.75 : 0
        Behavior on opacity {
            NumberAnimation {}
        }
    }
}
