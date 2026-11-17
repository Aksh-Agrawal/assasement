import QtQuick 2.15
import QtQuick.Controls 2.15
import ".." 1.0

Column {
    id: root
    objectName: "knowledgePanel"
    property var knowledge: null
    signal reviewRequested(string attempt, string question)
    signal checkRequested(string pack)
    property int page: 0
    property int pageSize: 5
    property string expandedKey: ""
    readonly property var overall: knowledge ? knowledge.overall : null
    readonly property var topics: knowledge ? knowledge.topics : []
    readonly property var trend: knowledge ? knowledge.trend : []
    spacing: Spacing.sm
    onKnowledgeChanged: {
        page = 0
        expandedKey = ""
    }

    component Caption: Text {
        width: parent.width
        wrapMode: Text.Wrap
        color: Theme.deepInk
        font.pixelSize: Typography.caption
        font.family: Typography.family
        textFormat: Text.PlainText
    }

    component Heading: Caption {
        font.family: Typography.familyEditorial
        font.pixelSize: Typography.sectionTitle
        font.bold: true
    }

    function percent(value) { return Math.round(value * 100) + "%" }

    function date(value) {
        return Qt.formatDate(new Date(value), "dd MMM yyyy")
    }

    AppCard {
        width: root.width
        height: reliability.implicitHeight + Spacing.md * 2
        Column {
            id: reliability
            x: Spacing.md
            y: Spacing.md
            width: parent.width - Spacing.md * 2
            spacing: Spacing.sm
            Heading { text: "Confidence and results" }
            Grid {
                width: parent.width
                columns: 2
                spacing: Spacing.xs
                Repeater {
                    model: [
                        {key: "confident_correct", title: "Confident and correct", tint: Theme.primaryLight},
                        {key: "confident_wrong", title: "Confident but incorrect", tint: Theme.terracottaLight},
                        {key: "uncertain_correct", title: "Uncertain but correct", tint: Theme.goldLight},
                        {key: "uncertain_wrong", title: "Uncertain and incorrect", tint: Theme.skyLight}
                    ]
                    delegate: Rectangle {
                        objectName: "knowledgeQuadrant-" + modelData.key
                        width: (reliability.width - Spacing.xs) / 2
                        height: Math.max(62, quadrantText.implicitHeight + Spacing.sm * 2)
                        radius: Metrics.radiusMedium
                        color: modelData.tint
                        border.color: modelData.key === "confident_wrong" ? Theme.terracotta : Theme.border
                        Column {
                            id: quadrantText
                            x: Spacing.sm
                            y: Spacing.sm
                            width: parent.width - Spacing.sm * 2
                            spacing: 2
                            Caption { text: modelData.title }
                            Caption {
                                font.bold: true
                                font.pixelSize: Typography.body
                                text: {
                                    if (!root.overall) return "—"
                                    var count = root.overall.quadrants[modelData.key]
                                    return count + (count === 1 ? " answer  ·  " : " answers  ·  ")
                                           + (root.overall.rated ? root.percent(root.overall.percentages[modelData.key]) : "—")
                                }
                            }
                        }
                    }
                }
            }
            Caption {
                text: root.overall ? root.overall.rated + " of " + root.overall.graded + " graded answers rated. "
                      + root.overall.unrated + " unrated · " + root.overall.skipped + " recorded skips · "
                      + root.overall.ungraded + " ungraded." : ""
            }
            Caption {
                visible: Boolean(root.overall) && root.overall.rated < root.knowledge.minimum_graded
                text: root.overall && root.overall.rated ? "Limited confidence evidence." : "Rate your confidence in practice to fill in the squares."
            }
        }
    }

    AppCard {
        visible: root.trend.length >= 2
        width: root.width
        height: history.implicitHeight + Spacing.md * 2
        Column {
            id: history
            x: Spacing.md
            y: Spacing.md
            width: parent.width - Spacing.md * 2
            spacing: Spacing.xs
            Heading { text: "Recent accuracy" }
            Caption { text: "Correct answers out of graded answers in each assessment." }
            Repeater {
                model: root.trend.length >= 2 ? root.trend : []
                delegate: Row {
                    width: history.width
                    spacing: Spacing.sm
                    Caption {
                        width: Math.min(210, parent.width * 0.55)
                        text: root.date(modelData.completed_at) + " · " + root.percent(modelData.accuracy)
                              + " · " + modelData.graded + " graded"
                    }
                    Rectangle {
                        width: Math.max(0, parent.width - Math.min(210, parent.width * 0.55) - Spacing.sm)
                        height: 6
                        radius: 3
                        anchors.verticalCenter: parent.verticalCenter
                        color: Theme.border
                        Rectangle { width: parent.width * modelData.accuracy; height: parent.height; radius: 3; color: Theme.forest }
                    }
                }
            }
        }
    }

    Heading { text: "Topic strengths" }
    Caption {
        text: !root.topics.length ? "Complete an assessment or open a local practice pack to see topics here."
             : root.knowledge.topic_count > root.topics.length ? "Showing " + root.topics.length + " of "
               + root.knowledge.topic_count + " topics available on this device."
             : "Accuracy uses graded answers in this attempt range."
    }
    Repeater {
        model: root.topics.slice(root.page * root.pageSize, (root.page + 1) * root.pageSize)
        delegate: Column {
            width: root.width
            spacing: Spacing.xs
            readonly property var topic: modelData
            readonly property bool opened: root.expandedKey === topic.key
            readonly property string topicLabel: topic.topic || "Unclassified topic"
            readonly property string groupLabel: (topic.subject || "Unclassified subject") + " / " + (topic.chapter || "Unclassified chapter")
            readonly property string resultLabel: topic.graded ? root.percent(topic.accuracy) + " accuracy · "
                + topic.graded + " graded" + (topic.graded < root.knowledge.minimum_graded ? " · Limited sample" : "")
                : topic.attempt_count ? "No graded answers" : "Unassessed"

            AbstractButton {
                id: tile
                objectName: "knowledgeTopicTile"
                width: parent.width
                height: Math.max(Metrics.touchNormal, tileContent.implicitHeight + Spacing.sm * 2)
                focusPolicy: Qt.StrongFocus
                Accessible.name: parent.topicLabel + ", " + parent.groupLabel + ", " + parent.resultLabel
                onClicked: root.expandedKey = parent.opened ? "" : parent.topic.key
                background: Rectangle {
                    radius: Metrics.radiusMedium
                    color: tile.down ? Theme.surfaceActive : tile.parent.topic.graded ? Theme.surfaceSelected : Theme.surface
                    border.color: tile.parent.opened || tile.visualFocus ? Theme.forest : Theme.border
                    border.width: tile.parent.opened || tile.visualFocus ? 2 : 1
                }
                contentItem: Column {
                    id: tileContent
                    spacing: 3
                    leftPadding: Spacing.sm
                    rightPadding: Spacing.sm
                    topPadding: Spacing.sm
                    bottomPadding: Spacing.sm
                    Caption { width: parent.width - Spacing.sm * 2; text: tile.parent.groupLabel }
                    Caption { width: parent.width - Spacing.sm * 2; font.bold: true; text: tile.parent.topicLabel }
                    Caption { width: parent.width - Spacing.sm * 2; text: tile.parent.resultLabel }
                    Rectangle {
                        visible: tile.parent.topic.graded > 0
                        width: parent.width - Spacing.sm * 2
                        height: 5
                        radius: 3
                        color: Theme.border
                        Rectangle {
                            width: parent.width * (tile.parent.topic.accuracy || 0)
                            height: parent.height
                            radius: 3
                            color: tile.parent.topic.quadrants.confident_wrong ? Theme.terracotta : Theme.forest
                        }
                    }
                }
            }

            AppCard {
                visible: parent.opened
                width: parent.width
                height: topicDetail.implicitHeight + Spacing.sm * 2
                Column {
                    id: topicDetail
                    readonly property var item: tile.parent.topic
                    x: Spacing.sm
                    y: Spacing.sm
                    width: parent.width - Spacing.sm * 2
                    spacing: Spacing.xs
                    Caption {
                        text: topicDetail.item.attempt_count + (topicDetail.item.attempt_count === 1 ? " attempt · " : " attempts · ")
                              + topicDetail.item.quadrants.confident_wrong
                              + " confident mistakes" + (topicDetail.item.last_practiced_at
                              ? " · Last practiced " + root.date(topicDetail.item.last_practiced_at) : "")
                    }
                    Caption {
                        visible: topicDetail.item.graded > 0
                        text: {
                            var item = topicDetail.item
                            return (item.confidence.sure.correct + item.confidence.sure.wrong) + " Sure · "
                                   + (item.confidence.not_sure.correct + item.confidence.not_sure.wrong) + " Not sure · "
                                   + (item.confidence.guessing.correct + item.confidence.guessing.wrong) + " Guessing · "
                                   + item.unrated + " unrated"
                        }
                    }
                    Caption {
                        visible: Boolean(topicDetail.item.retention)
                        text: ({due: "Retention check due", upcoming: "Retention check scheduled",
                                retained: "Retained after checks", reinforcement: "Needs reinforcement"})[topicDetail.item.retention] || ""
                    }
                    SecondaryButton {
                        visible: Boolean(topicDetail.item.downloaded_check)
                        text: "Start downloaded check"
                        onClicked: root.checkRequested(topicDetail.item.downloaded_check)
                    }
                    SecondaryButton {
                        objectName: "knowledgeReview"
                        visible: !topicDetail.item.downloaded_check && topicDetail.item.evidence.length > 0
                        text: "Review answer"
                        onClicked: {
                            var answer = topicDetail.item.evidence[0]
                            root.reviewRequested(answer.attempt_id, answer.question_id)
                        }
                    }
                }
            }
        }
    }
    Row {
        visible: root.topics.length > root.pageSize
        spacing: Spacing.sm
        SecondaryButton {
            text: "Previous topics"
            enabled: root.page > 0
            onClicked: { root.page--; root.expandedKey = "" }
        }
        SecondaryButton {
            text: "Next topics"
            enabled: (root.page + 1) * root.pageSize < root.topics.length
            onClicked: { root.page++; root.expandedKey = "" }
        }
    }
}
