import { app } from "../../scripts/app.js";

// Listen for AceTalk pushing a filled workflow
app.api.addEventListener("acetalk_load_workflow", async (event) => {
    const workflow = event.detail?.workflow;
    if (!workflow) return;

    try {
        await app.loadGraphData(workflow);
        console.log("[AceTalkBridge] Workflow loaded — canvas updated with sent tags/lyrics.");
    } catch (err) {
        console.warn("[AceTalkBridge] Could not load workflow:", err);
    }
});

console.log("[AceTalkBridge] Extension ready.");
