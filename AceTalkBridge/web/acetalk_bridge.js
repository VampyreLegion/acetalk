import { app } from "../../scripts/app.js";

// Listen for AceTalk pushing a filled workflow
app.api.addEventListener("acetalk_load_workflow", async (event) => {
    const workflow = event.detail?.workflow;
    if (!workflow) return;

    try {
        // Update node widget values in-place so ComfyUI doesn't open a new
        // "Unsaved Workflow" project. Match by node ID, skip link inputs
        // (those are arrays like [nodeId, outputIndex]).
        let updated = 0;
        for (const [nodeId, nodeData] of Object.entries(workflow)) {
            if (!nodeData?.inputs) continue;
            const graphNode = app.graph._nodes_by_id?.[parseInt(nodeId)];
            if (!graphNode) continue;
            for (const widget of (graphNode.widgets ?? [])) {
                const val = nodeData.inputs[widget.name];
                if (val !== undefined && !Array.isArray(val)) {
                    widget.value = val;
                    updated++;
                }
            }
        }
        app.graph.setDirtyCanvas(true, true);
        console.log(`[AceTalkBridge] ${updated} widget(s) updated in-place.`);
    } catch (err) {
        console.warn("[AceTalkBridge] Could not update nodes:", err);
    }
});

console.log("[AceTalkBridge] Extension ready.");
