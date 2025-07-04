import { AgentPanel } from "@/components/agent-panel";
import {
  ResizablePanelGroup,
  ResizablePanel,
  ResizableHandle,
} from "@/components/ui/resizable";

import { FileExplorer } from "@/components/file-explorer";

export default function Home() {
  return (
    <ResizablePanelGroup
      direction="horizontal"
      className="min-h-screen w-full rounded-lg border"
    >
      <ResizablePanel defaultSize={20}>
        <FileExplorer />
      </ResizablePanel>
      <ResizableHandle withHandle />
      <ResizablePanel defaultSize={55}>
        <iframe src="http://localhost:8080" className="w-full h-full border-0"></iframe>
      </ResizablePanel>
      <ResizableHandle withHandle />
      <ResizablePanel defaultSize={25}>
        <AgentPanel />
      </ResizablePanel>
    </ResizablePanelGroup>
  );
}