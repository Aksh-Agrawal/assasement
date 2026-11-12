import QtQuick 2.15
import ".." 1.0
import "../components" 1.0

Rectangle {
    id: root
    anchors.fill: parent
    color: Theme.background

    AppHeader {
        id: header
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        title: "Quick Add Questions"
        profileText: quickAddController.profileName ? quickAddController.profileName : appController.activeProfileName
        networkText: appController.networkLabel
        syncText: appController.syncLabel
        isOnline: appController.isOnline
        showBack: true
        onBackClicked: quickAddController.cancelQuickAdd()
    }

    Item {
        anchors.top: header.bottom
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.margins: Spacing.md

        // ---------------------------------------------------------------------
        // Left Column: QR Code & Fallback Short Code
        // ---------------------------------------------------------------------
        AppCard {
            id: leftCard
            width: 310
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            anchors.left: parent.left

            Item {
                anchors.fill: parent
                anchors.margins: Spacing.md

                Column {
                    anchors.top: parent.top
                    anchors.left: parent.left
                    anchors.right: parent.right
                    spacing: Spacing.sm

                    // QR Display Box
                    Rectangle {
                        width: 220
                        height: 220
                        anchors.horizontalCenter: parent.horizontalCenter
                        color: "#FFFFFF"
                        radius: Metrics.radiusMd
                        border.color: Theme.border
                        border.width: 1

                        Image {
                            id: qrImage
                            anchors.fill: parent
                            anchors.margins: 10
                            source: quickAddController.qrSource
                            fillMode: Image.PreserveAspectFit
                            smooth: false
                            visible: quickAddController.status !== "CREATING" && quickAddController.status !== "EXPIRED" && quickAddController.status !== "FAILED" && quickAddController.qrSource.length > 0
                        }

                        // Creating state indicator
                        Column {
                            anchors.centerIn: parent
                            spacing: Spacing.sm
                            visible: quickAddController.status === "CREATING"

                            Rectangle {
                                width: 36; height: 36; radius: 18
                                color: Theme.primaryLight
                                anchors.horizontalCenter: parent.horizontalCenter
                                Image {
                                    anchors.centerIn: parent
                                    width: 20; height: 20
                                    source: Assets.refresh
                                    fillMode: Image.PreserveAspectFit
                                }
                            }
                            Text {
                                text: "Generating QR…"
                                color: Theme.textSecondary
                                font.pixelSize: Typography.caption
                                font.family: Typography.fontFamily
                                anchors.horizontalCenter: parent.horizontalCenter
                            }
                        }

                        // Expired state overlay
                        Column {
                            anchors.centerIn: parent
                            spacing: Spacing.xs
                            visible: quickAddController.status === "EXPIRED"

                            Text {
                                text: "QR Expired"
                                color: Theme.warning
                                font.pixelSize: Typography.body
                                font.bold: true
                                font.family: Typography.fontFamily
                                anchors.horizontalCenter: parent.horizontalCenter
                            }
                            Text {
                                text: "Tap button below to renew"
                                color: Theme.textSecondary
                                font.pixelSize: Typography.caption
                                font.family: Typography.fontFamily
                                anchors.horizontalCenter: parent.horizontalCenter
                            }
                        }

                        // Failed state overlay
                        Column {
                            anchors.centerIn: parent
                            spacing: Spacing.xs
                            visible: quickAddController.status === "FAILED"
                            width: parent.width - 20

                            Text {
                                text: "Cannot Load QR"
                                color: Theme.error
                                font.pixelSize: Typography.body
                                font.bold: true
                                font.family: Typography.fontFamily
                                anchors.horizontalCenter: parent.horizontalCenter
                            }
                            Text {
                                text: quickAddController.statusText ? quickAddController.statusText : "Device not linked or cloud offline"
                                color: Theme.textSecondary
                                font.pixelSize: 11
                                font.family: Typography.fontFamily
                                wrapMode: Text.WordWrap
                                horizontalAlignment: Text.AlignHCenter
                                width: parent.width
                            }
                        }
                    }

                    // Fallback Code Container
                    Rectangle {
                        width: parent.width
                        height: 70
                        radius: Metrics.radiusSm
                        color: Theme.surfaceWarm
                        border.color: Theme.border
                        border.width: 1

                        Column {
                            anchors.centerIn: parent
                            spacing: 2

                            Text {
                                text: "Or enter code on phone:"
                                color: Theme.textSecondary
                                font.pixelSize: Typography.caption
                                font.family: Typography.fontFamily
                                anchors.horizontalCenter: parent.horizontalCenter
                            }

                            Text {
                                text: quickAddController.shortCode ? quickAddController.shortCode : "--------"
                                color: Theme.forest
                                font.pixelSize: 22
                                font.bold: true
                                font.letterSpacing: 2
                                font.family: Typography.fontFamily
                                anchors.horizontalCenter: parent.horizontalCenter
                            }

                            Text {
                                text: quickAddController.entryUrl ? ("at " + quickAddController.entryUrl) : "at web/quick-add"
                                color: Theme.textMuted
                                font.pixelSize: 11
                                font.family: Typography.fontFamily
                                anchors.horizontalCenter: parent.horizontalCenter
                            }
                        }
                    }

                    // Remaining time pill
                    Row {
                        anchors.horizontalCenter: parent.horizontalCenter
                        spacing: 6
                        visible: quickAddController.status !== "READY" && quickAddController.status !== "EXPIRED" && quickAddController.status !== "FAILED"

                        Image {
                            width: 14; height: 14
                            anchors.verticalCenter: parent.verticalCenter
                            source: Assets.history
                            fillMode: Image.PreserveAspectFit
                        }

                        Text {
                            anchors.verticalCenter: parent.verticalCenter
                            text: "Expires in: " + quickAddController.remainingTime
                            color: Theme.textSecondary
                            font.pixelSize: Typography.caption
                            font.family: Typography.fontFamily
                        }
                    }
                }
            }
        }

        // ---------------------------------------------------------------------
        // Right Column: Instructions, Status, Dynamic State & Action Buttons
        // ---------------------------------------------------------------------
        AppCard {
            id: rightCard
            anchors.left: leftCard.right
            anchors.leftMargin: Spacing.md
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.bottom: parent.bottom

            Item {
                anchors.fill: parent
                anchors.margins: Spacing.lg

                // Vertical Column stacking header, status, and dynamic action panels
                Column {
                    anchors.top: parent.top
                    anchors.left: parent.left
                    anchors.right: parent.right
                    spacing: Spacing.md

                    // 1. Heading
                    Column {
                        width: parent.width
                        spacing: 4

                        Text {
                            text: "Add Questions From Your Phone"
                            color: Theme.textPrimary
                            font.pixelSize: Typography.title
                            font.family: Typography.fontSerif
                            font.bold: true
                            width: parent.width
                        }

                        Text {
                            text: "Scan the QR code with your phone camera. No laptop or sign-in needed."
                            color: Theme.textSecondary
                            font.pixelSize: Typography.body
                            font.family: Typography.fontFamily
                            wrapMode: Text.WordWrap
                            width: parent.width
                        }
                    }

                    // 2. Status Badge Box
                    Rectangle {
                        width: parent.width
                        height: 48
                        radius: Metrics.radiusSm
                        color: Theme.surfaceWarm
                        border.color: Theme.border
                        border.width: 1

                        Row {
                            anchors.left: parent.left
                            anchors.leftMargin: Spacing.md
                            anchors.right: parent.right
                            anchors.rightMargin: Spacing.md
                            anchors.verticalCenter: parent.verticalCenter
                            spacing: Spacing.md

                            StatusBadge {
                                anchors.verticalCenter: parent.verticalCenter
                                text: {
                                    switch (quickAddController.status) {
                                        case "CREATING": return "Preparing";
                                        case "WAITING_FOR_PHONE": return "Waiting for phone";
                                        case "PHONE_CONNECTED": return "Phone connected";
                                        case "UPLOADING": return "Uploading";
                                        case "PROCESSING": return "Processing";
                                        case "NEEDS_REVIEW": return "Needs Review";
                                        case "SYNCING_TO_DEVICE": return "Syncing";
                                        case "READY": return "Ready to practice";
                                        case "EXPIRED": return "Expired";
                                        case "FAILED": return "Failed";
                                        default: return "Pending";
                                    }
                                }
                                statusType: {
                                    switch (quickAddController.status) {
                                        case "READY": return "success";
                                        case "PHONE_CONNECTED":
                                        case "UPLOADING":
                                        case "PROCESSING":
                                        case "SYNCING_TO_DEVICE": return "syncing";
                                        case "NEEDS_REVIEW":
                                        case "EXPIRED": return "warning";
                                        case "FAILED": return "error";
                                        default: return "neutral";
                                    }
                                }
                            }

                            Text {
                                anchors.verticalCenter: parent.verticalCenter
                                text: quickAddController.statusText
                                color: Theme.textPrimary
                                font.pixelSize: Typography.body
                                font.family: Typography.fontFamily
                                elide: Text.ElideRight
                                width: parent.width - 150
                            }
                        }
                    }

                    // 3. Dynamic State Area
                    // 3A. Failure Alert Card
                    Rectangle {
                        width: parent.width
                        height: 90
                        radius: Metrics.radiusSm
                        color: Theme.terracottaLight
                        border.color: Theme.terracotta
                        border.width: 1
                        visible: quickAddController.status === "FAILED"

                        Column {
                            anchors.fill: parent
                            anchors.margins: Spacing.sm
                            spacing: 4

                            Row {
                                spacing: 6
                                Text {
                                    text: "⚠"
                                    color: Theme.terracotta
                                    font.bold: true
                                    font.pixelSize: 14
                                    anchors.verticalCenter: parent.verticalCenter
                                }
                                Text {
                                    text: "Authentication / Connection Error"
                                    color: Theme.terracotta
                                    font.bold: true
                                    font.pixelSize: Typography.body
                                    font.family: Typography.fontFamily
                                    anchors.verticalCenter: parent.verticalCenter
                                }
                            }

                            Text {
                                text: quickAddController.errorMessage || "Please connect this device to your student account first."
                                color: Theme.textPrimary
                                font.pixelSize: Typography.caption
                                font.family: Typography.fontFamily
                                wrapMode: Text.WordWrap
                                width: parent.width
                            }
                        }
                    }

                    // 3B. Success / Ready State
                    Rectangle {
                        width: parent.width
                        height: 96
                        radius: Metrics.radiusSm
                        color: Theme.surfaceSelected
                        border.color: Theme.sage
                        border.width: 1
                        visible: quickAddController.status === "READY"

                        Column {
                            anchors.fill: parent
                            anchors.margins: Spacing.sm
                            spacing: 4

                            Row {
                                spacing: Spacing.sm
                                Rectangle {
                                    width: 24; height: 24; radius: 12
                                    color: Theme.forest
                                    anchors.verticalCenter: parent.verticalCenter
                                    Image {
                                        anchors.centerIn: parent
                                        width: 14; height: 14
                                        source: Assets.check
                                        fillMode: Image.PreserveAspectFit
                                    }
                                }
                                Text {
                                    anchors.verticalCenter: parent.verticalCenter
                                    text: "Successfully Installed!"
                                    color: Theme.forest
                                    font.bold: true
                                    font.pixelSize: Typography.body
                                    font.family: Typography.fontFamily
                                }
                            }

                            Text {
                                text: quickAddController.packTitle ? quickAddController.packTitle : "Mobile Question Pack"
                                color: Theme.textPrimary
                                font.bold: true
                                font.pixelSize: Typography.body
                                font.family: Typography.fontFamily
                                elide: Text.ElideRight
                                width: parent.width
                            }

                            Text {
                                text: quickAddController.questionCount + " questions added to Practice"
                                color: Theme.textSecondary
                                font.pixelSize: Typography.caption
                                font.family: Typography.fontFamily
                            }
                        }
                    }

                    // 3C. Normal Instructional Steps (when not ready or failed)
                    Column {
                        width: parent.width
                        spacing: Spacing.sm
                        visible: quickAddController.status !== "READY" && quickAddController.status !== "FAILED" && quickAddController.status !== "EXPIRED"

                        Row {
                            spacing: Spacing.sm
                            Rectangle {
                                width: 22; height: 22; radius: 11
                                color: Theme.surfaceActive
                                Text { anchors.centerIn: parent; text: "1"; font.bold: true; font.pixelSize: 12; color: Theme.textPrimary }
                            }
                            Text {
                                anchors.verticalCenter: parent.verticalCenter
                                text: "Scan QR code with your phone camera"
                                color: Theme.textSecondary
                                font.pixelSize: Typography.body
                                font.family: Typography.fontFamily
                            }
                        }

                        Row {
                            spacing: Spacing.sm
                            Rectangle {
                                width: 22; height: 22; radius: 11
                                color: Theme.surfaceActive
                                Text { anchors.centerIn: parent; text: "2"; font.bold: true; font.pixelSize: 12; color: Theme.textPrimary }
                            }
                            Text {
                                anchors.verticalCenter: parent.verticalCenter
                                text: "Upload PDF or type questions directly"
                                color: Theme.textSecondary
                                font.pixelSize: Typography.body
                                font.family: Typography.fontFamily
                            }
                        }

                        Row {
                            spacing: Spacing.sm
                            Rectangle {
                                width: 22; height: 22; radius: 11
                                color: Theme.surfaceActive
                                Text { anchors.centerIn: parent; text: "3"; font.bold: true; font.pixelSize: 12; color: Theme.textPrimary }
                            }
                            Text {
                                anchors.verticalCenter: parent.verticalCenter
                                text: "Confirm and practice right here on Pi"
                                color: Theme.textSecondary
                                font.pixelSize: Typography.body
                                font.family: Typography.fontFamily
                            }
                        }
                    }
                }

                // Bottom Buttons pinned to bottom-right of the card
                Row {
                    id: buttonRow
                    anchors.bottom: parent.bottom
                    anchors.right: parent.right
                    spacing: Spacing.sm

                    // Unlinked device CTA
                    SecondaryButton {
                        visible: quickAddController.status === "FAILED" && (quickAddController.statusText.indexOf("not linked") !== -1 || quickAddController.errorMessage.indexOf("account") !== -1 || quickAddController.errorMessage.indexOf("Settings") !== -1)
                        text: "Pair Device"
                        iconSource: Assets.device_pairing
                        onClicked: appController.navigate("pairing")
                    }

                    // Retry button
                    PrimaryButton {
                        visible: quickAddController.status === "FAILED" || quickAddController.status === "EXPIRED"
                        text: "Try Again"
                        iconSource: Assets.refresh
                        onClicked: quickAddController.retryQuickAdd()
                    }

                    // Ready actions
                    PrimaryButton {
                        visible: quickAddController.status === "READY"
                        text: "Practice Now"
                        iconSource: Assets.practice
                        onClicked: quickAddController.practiceNow()
                    }

                    SecondaryButton {
                        visible: quickAddController.status === "READY"
                        text: "Done"
                        onClicked: appController.navigate("content")
                    }

                    // Cancel action (when not ready)
                    SecondaryButton {
                        visible: quickAddController.status !== "READY"
                        text: "Cancel"
                        onClicked: quickAddController.cancelQuickAdd()
                    }
                }
            }
        }
    }
}
