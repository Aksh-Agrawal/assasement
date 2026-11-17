import QtQuick 2.15
import QtQuick.Controls 2.15
import ".." 1.0
import "../components" 1.0

Rectangle {
    id: root
    anchors.fill: parent
    color: Theme.canvas
    property var metrics: assessmentController.progressMetrics
    property var intelligence: assessmentController.progressIntelligence
    property int sectionIndex: 0
    property int detailPage: 0
    property int pageSize: 5
    property var details: {
        if (sectionIndex === 1) return intelligence.knowledge ? intelligence.knowledge.topics : []
        if (sectionIndex === 2) return intelligence.recovery || []
        if (sectionIndex === 3) return intelligence.retention || []
        return []
    }
    Component.onCompleted: assessmentController.refreshProgress()

    component AnalyticsText: Text {
        width: parent.width
        wrapMode: Text.WordWrap
        color: Theme.mutedInk
        font.pixelSize: Typography.caption
        font.family: Typography.family
    }

    component AnalyticsHeading: AnalyticsText {
        color: Theme.deepInk
        font.pixelSize: Typography.sectionTitle
        font.family: Typography.familyEditorial
        font.bold: true
    }

    function percent(value) {
        return value === null || value === undefined ? "—" : Math.round(value * 100) + "%"
    }

    function durationLabel(milliseconds) {
        var minutes = Math.floor(milliseconds / 60000)
        if (milliseconds < 1000) return "<1 sec"
        if (milliseconds < 60000) return Math.floor(milliseconds / 1000) + " sec"
        var hours = Math.floor(minutes / 60)
        minutes = minutes % 60
        if (hours > 0) return hours + "h " + minutes + "m"
        return minutes + "m"
    }

    Row {
        anchors.fill: parent

        NavRail {
            width: Metrics.navRailWidth
            height: parent.height
            currentTab: "progress"
            onTabSelected: function(tab) {
                if (tab === "home") appController.navigate("home")
                else if (tab === "library") appController.navigate("subjects")
                else if (tab === "practice") appController.navigate("content")
                else if (tab === "progress") appController.navigate("progress")
                else if (tab === "history") appController.navigate("history")
                else if (tab === "settings") appController.navigate("settings")
            }
        }

        Column {
            width: parent.width - Metrics.navRailWidth
            height: parent.height

            AppHeader {
                width: parent.width
                title: "Analytics"
                profileText: appController.activeProfileName
                networkText: appController.networkLabel
                syncText: appController.syncLabel
                isOnline: appController.isOnline
            }

            Flickable {
                id: content
                objectName: "progressAnalyticsFlickable"
                width: parent.width
                height: parent.height - Metrics.headerHeight
                contentWidth: width
                contentHeight: body.implicitHeight + Spacing.md * 2
                clip: true
                boundsBehavior: Flickable.StopAtBounds

                Column {
                    id: body
                    width: parent.width - Spacing.md * 2
                    x: Spacing.md
                    y: Spacing.sm
                    spacing: Spacing.sm

                    Row {
                        width: parent.width
                        spacing: Spacing.xs
                        Repeater {
                            model: ["Overview", "Knowledge Map", "Recovery", "Retention", "Exam Strategy"]
                            delegate: SecondaryButton {
                                width: (body.width - Spacing.xs * 4) / 5
                                preferredHeight: Metrics.touchNormal
                                text: modelData
                                enabled: index !== root.sectionIndex
                                onClicked: {
                                    root.sectionIndex = index
                                    root.detailPage = 0
                                    content.contentY = 0
                                }
                            }
                        }
                    }

                    Row {
                        width: parent.width
                        height: Metrics.touchNormal
                        spacing: Spacing.sm

                        ComboBox {
                            width: 128
                            height: parent.height
                            popup.topMargin: Metrics.touchSafeInset
                            popup.bottomMargin: Metrics.touchSafeInset
                            model: [5, 10, 20]
                            currentIndex: [5, 10, 20].indexOf(assessmentController.analyticsWindow)
                            displayText: "Last " + currentValue
                            font.pixelSize: Typography.caption
                            Accessible.name: "Attempt range"
                            onActivated: {
                                root.detailPage = 0
                                assessmentController.setAnalyticsWindow(Number(currentValue))
                            }
                        }
                        AnalyticsText {
                            width: parent.width - 138
                            anchors.verticalCenter: parent.verticalCenter
                            text: assessmentController.progressBusy ? "Updating analytics…" :
                                  intelligence.pending ? "Local results waiting to sync." :
                                  intelligence.limited ? "Some attempts have limited question evidence." :
                                  intelligence.linked && !appController.isOnline ? "Offline · showing saved evidence." : ""
                        }
                    }

                    AnalyticsText {
                        visible: Boolean(intelligence.failed)
                        text: "Analytics could not load. Reopen Analytics to retry."
                    }

                    AppCard {
                        visible: root.sectionIndex === 0
                        width: parent.width
                        height: 94

                        Row {
                            anchors.fill: parent
                            anchors.margins: Spacing.md
                            spacing: Spacing.md

                            Column {
                                width: parent.width - viewHistory.width - Spacing.md
                                anchors.verticalCenter: parent.verticalCenter
                                spacing: 5

                                AnalyticsHeading {
                                    text: metrics.attempts + " of last " + assessmentController.analyticsWindow + " assessments"
                                }

                                Text {
                                    text: "Accuracy " + (metrics.accuracyPercent < 0 ? "Not enough answers yet" : metrics.accuracyPercent + "%")
                                          + "   •   " + metrics.correct + " correct   •   " + metrics.wrong + " incorrect   •   " + metrics.skipped + " skipped"
                                    color: Theme.mutedInk
                                    font.pixelSize: Typography.caption
                                    font.family: Typography.family
                                    elide: Text.ElideRight
                                    width: parent.width
                                }

                                Text {
                                    text: "Practice " + root.durationLabel(metrics.practiceTimeMs)
                                          + "   •   " + metrics.deviceAttempts + " on Pi   •   " + metrics.webAttempts + " on web"
                                    color: Theme.mutedInk
                                    font.pixelSize: Typography.caption
                                    font.family: Typography.family
                                    elide: Text.ElideRight
                                    width: parent.width
                                }
                            }

                            SecondaryButton {
                                id: viewHistory
                                anchors.verticalCenter: parent.verticalCenter
                                text: "History"
                                preferredHeight: Metrics.touchNormal
                                onClicked: appController.navigate("history")
                            }
                        }
                    }

                    AppCard {
                        visible: root.sectionIndex === 0
                        width: parent.width
                        height: 152

                        Column {
                            anchors.fill: parent
                            anchors.margins: Spacing.md
                            spacing: 6

                            Text {
                                text: "Accuracy over recent assessments"
                                color: Theme.deepInk
                                font.pixelSize: Typography.sectionTitle
                                font.bold: true
                                font.family: Typography.familyEditorial
                            }

                            Item {
                                width: parent.width
                                height: 92

                                Text {
                                    anchors.centerIn: parent
                                    visible: metrics.trends.length === 0
                                    text: "Complete an assessment to start a trend."
                                    color: Theme.mutedInk
                                    font.pixelSize: Typography.caption
                                }

                                Row {
                                    anchors.fill: parent
                                    spacing: 8
                                    visible: metrics.trends.length > 0

                                    Repeater {
                                        model: metrics.trends

                                        delegate: Column {
                                            width: (parent.width - 8 * (metrics.trends.length - 1)) / Math.max(1, metrics.trends.length)
                                            height: parent.height
                                            spacing: 3

                                            Item {
                                                width: parent.width
                                            height: 58

                                                Rectangle {
                                                    anchors.bottom: parent.bottom
                                                    anchors.horizontalCenter: parent.horizontalCenter
                                                    width: Math.min(28, parent.width - 4)
                                                    height: modelData.accuracyPercent < 0 ? 2 : Math.max(4, 54 * modelData.accuracyPercent / 100)
                                                    radius: 4
                                                    color: modelData.accuracyPercent < 0 ? Theme.border : Theme.forest
                                                }
                                            }

                                            Text {
                                                width: parent.width
                                                horizontalAlignment: Text.AlignHCenter
                                                text: modelData.accuracyPercent < 0 ? "–" : modelData.accuracyPercent + "%"
                                                color: Theme.deepInk
                                                font.pixelSize: 10
                                                font.bold: true
                                            }

                                            Text {
                                                width: parent.width
                                                horizontalAlignment: Text.AlignHCenter
                                                text: modelData.label
                                                color: Theme.mutedInk
                                                font.pixelSize: 8
                                                elide: Text.ElideRight
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }

                    AppCard {
                        visible: root.sectionIndex === 0
                        width: parent.width
                        height: 184

                        Column {
                            anchors.fill: parent
                            anchors.margins: Spacing.md
                            spacing: 4

                            Text {
                                text: "Confidence check"
                                color: Theme.deepInk
                                font.pixelSize: Typography.sectionTitle
                                font.bold: true
                                font.family: Typography.familyEditorial
                            }

                            Text {
                                text: "See how your confidence matched your answers."
                                color: Theme.mutedInk
                                font.pixelSize: Typography.caption
                                font.family: Typography.family
                            }

                            Repeater {
                                model: [
                                    {key: "sure", label: "Sure"},
                                    {key: "not_sure", label: "Not sure"},
                                    {key: "guessing", label: "Guessing"},
                                    {key: "unrated", label: "No confidence rating"}
                                ]

                                delegate: Row {
                                    width: parent.width
                                    height: 22
                                    spacing: 8

                                    Text {
                                        width: 120
                                        anchors.verticalCenter: parent.verticalCenter
                                        text: modelData.label
                                        color: Theme.deepInk
                                        font.pixelSize: Typography.caption
                                        font.family: Typography.family
                                        elide: Text.ElideRight
                                    }

                                    Text {
                                        width: 110
                                        anchors.verticalCenter: parent.verticalCenter
                                        text: metrics.confidence[modelData.key].correct + " correct · " + metrics.confidence[modelData.key].wrong + " incorrect"
                                        color: Theme.mutedInk
                                        font.pixelSize: Typography.caption
                                        font.family: Typography.family
                                    }

                                    Rectangle {
                                        width: parent.width - 246
                                        height: 7
                                        anchors.verticalCenter: parent.verticalCenter
                                        radius: 4
                                        color: Theme.borderLight

                                        Rectangle {
                                            width: {
                                                var total = metrics.confidence[modelData.key].correct + metrics.confidence[modelData.key].wrong
                                                return total > 0 ? parent.width * metrics.confidence[modelData.key].correct / total : 0
                                            }
                                            height: parent.height
                                            radius: parent.radius
                                            color: Theme.forest
                                        }
                                    }
                                }
                            }

                            Text {
                                objectName: "averageAnswerTimeText"
                                text: "Average answer time: " + (metrics.averageResponseTimeMs < 0 ? "–" : Math.round(metrics.averageResponseTimeMs / 1000) + " sec")
                                color: Theme.mutedInk
                                font.pixelSize: Typography.caption
                                font.family: Typography.family
                            }
                        }
                    }

                    AppCard {
                        visible: root.sectionIndex === 1
                        width: parent.width
                        height: reliabilityBody.implicitHeight + Spacing.md * 2

                        Column {
                            id: reliabilityBody
                            x: Spacing.md
                            y: Spacing.md
                            width: parent.width - Spacing.md * 2
                            spacing: Spacing.xs
                            property var view: intelligence.knowledge ? intelligence.knowledge.overall : null
                            AnalyticsHeading { text: "Confidence and results" }
                            AnalyticsText {
                                text: reliabilityBody.view ? reliabilityBody.view.rated + " of " + reliabilityBody.view.graded
                                      + " graded answers rated · " + reliabilityBody.view.unrated + " unrated · "
                                      + reliabilityBody.view.skipped + " recorded skips · " + reliabilityBody.view.ungraded
                                      + " ungraded" : "No locally available evidence."
                            }
                            Repeater {
                                model: [{key: "confident_correct", title: "Confident and correct"},
                                        {key: "confident_wrong", title: "Confident but wrong"},
                                        {key: "uncertain_correct", title: "Uncertain but correct"},
                                        {key: "uncertain_wrong", title: "Uncertain and wrong"}]
                                delegate: AnalyticsText {
                                    text: modelData.title + (reliabilityBody.view ? "  "
                                          + reliabilityBody.view.quadrants[modelData.key] + "  ·  "
                                          + root.percent(reliabilityBody.view.percentages[modelData.key]) : "")
                                }
                            }
                            AnalyticsText {
                                text: "Topic details use the question evidence available on this device."
                            }
                        }
                    }

                    AnalyticsText {
                        visible: root.sectionIndex >= 1 && root.sectionIndex <= 3
                                 && root.details.length === 0 && !assessmentController.progressBusy
                        text: root.sectionIndex === 1 ? "No topic details for these attempts." :
                              !intelligence.checks_cached ? "Sync your linked profile to see its check schedule." :
                              root.sectionIndex === 2 ? "No recovery recommendations." : "No retention checks scheduled."
                    }

                    AnalyticsText {
                        visible: (root.sectionIndex === 2 || root.sectionIndex === 3) && Boolean(intelligence.checks_limited)
                        text: "This device shows the first 100 checks. See the full schedule on the web."
                    }

                    Repeater {
                        model: root.details.slice(root.detailPage * root.pageSize, (root.detailPage + 1) * root.pageSize)
                        delegate: AppCard {
                            width: body.width
                            height: topicBody.implicitHeight + Spacing.md * 2

                            Column {
                                id: topicBody
                                x: Spacing.md
                                y: Spacing.md
                                width: parent.width - Spacing.md * 2
                                spacing: Spacing.xs
                                property var answer: root.sectionIndex === 1 && modelData.evidence && modelData.evidence.length
                                                     ? modelData.evidence[0] : null

                                AnalyticsHeading { text: modelData.topic }
                                AnalyticsText { text: modelData.subject + " · " + modelData.chapter }
                                AnalyticsText {
                                    text: root.sectionIndex === 1 ? root.percent(modelData.accuracy) + " accuracy across "
                                          + modelData.graded + " graded" + (!modelData.gap ? "" : modelData.gap === "repeated"
                                          ? " · Repeated confident mistakes" : " · Possible understanding gap") :
                                          root.sectionIndex === 2 ? (modelData.status === "ready" ? "Ready to check" :
                                          modelData.status === "recovered" ? "Recovered" : modelData.status === "waiting" ?
                                          "Scheduled for " + modelData.local_due : modelData.status === "no_questions" ?
                                          "Awaiting a fresh question" : modelData.status === "dismissed" ?
                                          "Dismissed" : "Check in progress") :
                                          modelData.local_status ? modelData.local_status + " · Day " + modelData.day
                                          + " · " + modelData.local_due : modelData.status === "retained"
                                          ? "Retained after delayed checks" : "Needs reinforcement"
                                }
                                AnalyticsText {
                                    visible: root.sectionIndex !== 1 && Boolean(modelData.pi_pack_id)
                                    text: modelData.pending_completion ? "Check completed on this device. Awaiting reconciliation." :
                                          modelData.can_open_pack ? "Downloaded · available offline" : "Waiting to download on sync"
                                }
                                SecondaryButton {
                                    visible: root.sectionIndex !== 1 && Boolean(modelData.can_open_pack)
                                    text: "Start downloaded check"
                                    preferredHeight: Metrics.touchNormal
                                    onClicked: assessmentController.startDownloadedCheck(modelData.pi_pack_id)
                                }
                                SecondaryButton {
                                    visible: Boolean(topicBody.answer)
                                    text: "Review answer"
                                    preferredHeight: Metrics.touchNormal
                                    onClicked: assessmentController.openHistoryReview(topicBody.answer.attempt_id, topicBody.answer.question_id)
                                }
                                Repeater {
                                    model: root.sectionIndex === 3 ? (modelData.history || []) : []
                                    delegate: SecondaryButton {
                                        text: "Review Day " + modelData.day + (modelData.passed ? " · Passed" : " · Needs reinforcement")
                                        preferredHeight: Metrics.touchNormal
                                        onClicked: assessmentController.openHistoryReview(modelData.attempt_id, modelData.question_id)
                                    }
                                }
                            }
                        }
                    }

                    Row {
                        visible: root.details.length > root.pageSize
                        spacing: Spacing.sm
                        SecondaryButton {
                            text: "Previous"
                            enabled: root.detailPage > 0
                            preferredHeight: Metrics.touchNormal
                            onClicked: { root.detailPage--; content.contentY = 0 }
                        }
                        SecondaryButton {
                            text: "Next"
                            enabled: (root.detailPage + 1) * root.pageSize < root.details.length
                            preferredHeight: Metrics.touchNormal
                            onClicked: { root.detailPage++; content.contentY = 0 }
                        }
                    }

                    AppCard {
                        visible: root.sectionIndex === 4
                        width: parent.width
                        height: strategyBody.implicitHeight + Spacing.md * 2
                        Column {
                            id: strategyBody
                            x: Spacing.md
                            y: Spacing.md
                            width: parent.width - Spacing.md * 2
                            spacing: Spacing.sm
                            property var strategy: intelligence.strategy || null
                            property var labels: ({attempt_all: "Attempt all", above_break_even: "Attempt above break-even",
                                                   skip_uncertain: "Skip uncertain", revisit: "Revisit harder questions"})
                            AnalyticsHeading { text: "Latest completed assessment" }
                            AnalyticsText {
                                text: strategyBody.strategy ? strategyBody.strategy.available_attempts[0].title
                                      : "No marking scheme is available. Sync newer web results or finish a local assessment."
                            }
                            AnalyticsText {
                                visible: Boolean(strategyBody.strategy)
                                text: strategyBody.strategy ? strategyBody.strategy.marking.correct + " correct · "
                                      + strategyBody.strategy.marking.wrong + " wrong · " + strategyBody.strategy.marking.skip
                                      + " skip · Break-even " + root.percent(strategyBody.strategy.break_even.threshold) : ""
                            }
                            AnalyticsText {
                                visible: Boolean(strategyBody.strategy)
                                text: strategyBody.strategy ? strategyBody.strategy.modelled_questions + " of "
                                      + strategyBody.strategy.recorded_questions + " answers have enough earlier rated evidence."
                                      + (strategyBody.strategy.modelled_questions ? " Expected marks are estimates." : "") : ""
                            }
                            Repeater {
                                model: strategyBody.strategy && strategyBody.strategy.modelled_questions
                                       ? strategyBody.strategy.comparisons : []
                                delegate: AnalyticsText {
                                    text: strategyBody.labels[modelData.strategy] + " · " + modelData.expected_marks
                                          + " expected marks · " + modelData.attempted + " attempted · "
                                          + root.durationLabel(modelData.known_time_ms)
                                          + (modelData.missing_time ? " recorded · some timing missing" : "")
                                }
                            }
                            SecondaryButton {
                                id: strategyOptions
                                property bool expanded: false
                                visible: Boolean(strategyBody.strategy)
                                text: expanded ? "Hide marking options" : "Edit marking and time budget"
                                preferredHeight: Metrics.touchNormal
                                onClicked: expanded = !expanded
                            }
                            Flow {
                                width: parent.width
                                spacing: Spacing.sm
                                visible: strategyOptions.expanded && Boolean(strategyBody.strategy)
                                Repeater {
                                    id: markingFields
                                    model: ["correct", "wrong", "skip", "minutes"]
                                    delegate: Column {
                                        width: 108
                                        AnalyticsText { text: modelData === "minutes" ? "Revisit minutes" : modelData + " marks" }
                                        TextField {
                                            id: marksInput
                                            width: parent.width
                                            height: Metrics.touchNormal
                                            Accessible.name: modelData === "minutes" ? "Revisit minutes" : modelData + " marks"
                                            inputMethodHints: Qt.ImhFormattedNumbersOnly
                                            text: modelData === "minutes" ? "0" : strategyBody.strategy
                                                  ? String(strategyBody.strategy.marking[modelData]) : ""
                                        }
                                        function entered() { return Number(marksInput.text) }
                                    }
                                }
                            }
                            SecondaryButton {
                                visible: strategyOptions.expanded && Boolean(strategyBody.strategy)
                                text: "Compare"
                                enabled: !assessmentController.progressBusy
                                preferredHeight: Metrics.touchNormal
                                onClicked: assessmentController.simulateStrategy(markingFields.itemAt(0).entered(),
                                           markingFields.itemAt(1).entered(), markingFields.itemAt(2).entered(),
                                           markingFields.itemAt(3).entered())
                            }
                        }
                    }
                }
            }
        }
    }
}
