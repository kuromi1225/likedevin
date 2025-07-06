'use client';

import { useState, useEffect, useRef } from 'react';
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Settings, Check, X } from 'lucide-react';
import { SettingsModal } from './settings-modal'; // 新しくインポート

interface AgentMessage {
  type: string;
  content?: any;
  tasks?: string[];
  task_index?: number;
  status?: string;
  command?: string;
  output?: string;
  question?: string;
}

interface AskState {
  isAsking: boolean;
  question: string;
}

export function AgentPanel() {
  const [prompt, setPrompt] = useState('');
  const [messages, setMessages] = useState<AgentMessage[]>([]);
  const agentWs = useRef<WebSocket | null>(null);
  const askWs = useRef<WebSocket | null>(null);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [askState, setAskState] = useState<AskState>({ isAsking: false, question: '' });

  const setupWebSockets = () => {
    // Agent WebSocket
    agentWs.current = new WebSocket('ws://localhost:8000/ws/agent');
    agentWs.current.onmessage = (event) => {
      const message = JSON.parse(event.data);
      setMessages((prev) => [...prev, message]);
    };
    agentWs.current.onopen = () => setMessages((prev) => [...prev, { type: 'log', content: 'Agent connection established' }]);
    agentWs.current.onclose = () => {
        setMessages((prev) => [...prev, { type: 'log', content: 'Agent connection closed. Reconnecting...' }]);
        setTimeout(setupWebSockets, 3000); // 3秒後に再接続
    };

    // Ask WebSocket
    askWs.current = new WebSocket('ws://localhost:8000/ws/ask');
    askWs.current.onmessage = (event) => {
      const message = JSON.parse(event.data);
      if (message.type === 'ask') {
        setAskState({ isAsking: true, question: message.question });
      }
    };
     askWs.current.onopen = () => setMessages((prev) => [...prev, { type: 'log', content: 'Ask connection established' }]);
     askWs.current.onclose = () => {
        setMessages((prev) => [...prev, { type: 'log', content: 'Ask connection closed. Reconnecting...' }]);
        // Agent WSの再接続ロジックに任せる
    };

  };

  useEffect(() => {
    setupWebSockets();
    return () => {
      agentWs.current?.close();
      askWs.current?.close();
    };
  }, []);

  const handleStartTask = async () => {
    if (prompt.trim() === '') return;
    try {
        const response = await fetch('http://localhost:8000/api/task/start', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ prompt }),
        });
        if(response.ok) {
            setMessages((prev) => [...prev, { type: 'user_prompt', content: `Task started: ${prompt}` }]);
            setPrompt('');
        }
    } catch (error) {
        setMessages((prev) => [...prev, { type: 'error', content: 'Failed to start task' }]);
    }
  };

  const handleAskResponse = (answer: 'yes' | 'no') => {
    askWs.current?.send(JSON.stringify({ answer }));
    setAskState({ isAsking: false, question: '' });
  };


  const renderMessage = (msg: AgentMessage, index: number) => {
    switch (msg.type) {
        case 'thought':
            return <p key={index} className="text-sm text-gray-400 italic">🤔 {msg.content}</p>;
        case 'subtasks':
            return <div key={index}><p className="font-bold">✅ Plan:</p><ol className="list-decimal list-inside">{msg.tasks?.map((task, i) => <li key={i}>{task}</li>)}</ol></div>;
        case 'command_result':
            return <div key={index} className="p-2 bg-gray-800 rounded font-mono text-xs"><p className="text-green-400">$ {msg.command}</p><pre className="whitespace-pre-wrap">{msg.output}</pre></div>;
        case 'error':
            return <p key={index} className="text-sm text-red-500">❌ Error: {msg.content}</p>;
        case 'log':
             return <p key={index} className="text-xs text-blue-400">ℹ️ {msg.content}</p>;
        case 'user_prompt':
             return <p key={index} className="font-bold">🚀 {msg.content}</p>;
        default:
            return <p key={index} className="text-sm">{JSON.stringify(msg)}</p>;
    }
  }

  return (
    <>
      <SettingsModal isOpen={isSettingsOpen} onClose={() => setIsSettingsOpen(false)} />
      <Card className="h-full flex flex-col">
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>Agent Control Panel</CardTitle>
          <Button variant="ghost" size="icon" onClick={() => setIsSettingsOpen(true)}>
            <Settings className="h-5 w-5" />
          </Button>
        </CardHeader>
        <CardContent className="flex-grow flex flex-col gap-4">
          <div className="flex w-full items-center space-x-2">
            <Input
              type="text"
              placeholder="Enter your task prompt..."
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleStartTask()}
              disabled={askState.isAsking}
            />
            <Button onClick={handleStartTask} disabled={askState.isAsking}>Start Task</Button>
          </div>
          <ScrollArea className="flex-grow border rounded-md p-4 bg-background">
              <div className="flex flex-col gap-2">
                  {messages.map(renderMessage)}
              </div>
          </ScrollArea>
           {askState.isAsking && (
            <div className="border-t p-4 flex flex-col gap-2">
                <p className="font-semibold text-yellow-500">❓ Agent needs your input:</p>
                <p>{askState.question}</p>
                <div className="flex gap-2 justify-end">
                    <Button variant="outline" size="sm" onClick={() => handleAskResponse('no')}>
                        <X className="mr-1 h-4 w-4" /> No
                    </Button>
                    <Button variant="default" size="sm" onClick={() => handleAskResponse('yes')}>
                        <Check className="mr-1 h-4 w-4" /> Yes
                    </Button>
                </div>
            </div>
          )}
        </CardContent>
      </Card>
    </>
  );
}