
'use client';

import { useState, useEffect, useRef } from 'react';
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";

interface AgentMessage {
  type: string;
  content?: any;
  tasks?: any[];
  task_index?: number;
  status?: string;
  command?: string;
  output?: string;
}

export function AgentPanel() {
  const [prompt, setPrompt] = useState('');
  const [messages, setMessages] = useState<AgentMessage[]>([]);
  const ws = useRef<WebSocket | null>(null);

  useEffect(() => {
    ws.current = new WebSocket('ws://localhost:8000/ws/agent');

    ws.current.onmessage = (event) => {
      const message = JSON.parse(event.data);
      setMessages((prev) => [...prev, message]);
    };

    ws.current.onopen = () => {
        setMessages((prev) => [...prev, { type: 'log', content: 'WebSocket connected' }]);
    };

    ws.current.onerror = (error) => {
        setMessages((prev) => [...prev, { type: 'error', content: 'WebSocket error' }]);
        console.error('WebSocket error:', error);
    };

    ws.current.onclose = () => {
        setMessages((prev) => [...prev, { type: 'log', content: 'WebSocket disconnected' }]);
    };

    return () => {
      ws.current?.close();
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
            setMessages((prev) => [...prev, { type: 'log', content: `Task started: ${prompt}` }]);
            setPrompt('');
        }
    } catch (error) {
        setMessages((prev) => [...prev, { type: 'error', content: 'Failed to start task' }]);
    }
  };

  const renderMessage = (msg: AgentMessage, index: number) => {
    switch (msg.type) {
        case 'thought':
            return <p key={index} className="text-sm text-gray-400 italic">{msg.content}</p>;
        case 'subtasks':
            return <div key={index}><p className="font-bold">Subtasks:</p><ol className="list-decimal list-inside">{msg.tasks?.map((task, i) => <li key={i}>{task}</li>)}</ol></div>;
        case 'command_result':
            return <div key={index} className="p-2 bg-gray-800 rounded font-mono text-xs"><p className="text-green-400">$ {msg.command}</p><p>{msg.output}</p></div>;
        case 'error':
            return <p key={index} className="text-sm text-red-500">Error: {msg.content}</p>;
        default:
            return <p key={index} className="text-sm">{JSON.stringify(msg)}</p>;
    }
  }

  return (
    <Card className="h-full flex flex-col">
      <CardHeader>
        <CardTitle>Agent Control Panel</CardTitle>
      </CardHeader>
      <CardContent className="flex-grow flex flex-col gap-4">
        <div className="flex w-full items-center space-x-2">
          <Input
            type="text"
            placeholder="Enter your task prompt..."
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleStartTask()}
          />
          <Button onClick={handleStartTask}>Start Task</Button>
        </div>
        <ScrollArea className="flex-grow border rounded-md p-4">
            <div className="flex flex-col gap-2">
                {messages.map(renderMessage)}
            </div>
        </ScrollArea>
      </CardContent>
    </Card>
  );
}
