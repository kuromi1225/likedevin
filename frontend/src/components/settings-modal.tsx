'use client';

import { useState, useEffect } from 'react';
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select"

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function SettingsModal({ isOpen, onClose }: SettingsModalProps) {
  const [llmModel, setLlmModel] = useState('maverick');
  const [repoUrl, setRepoUrl] = useState('');

  // モーダルが開いた時に現在の設定をバックエンドから取得
  useEffect(() => {
    if (isOpen) {
      const fetchSettings = async () => {
        try {
          const response = await fetch('http://localhost:8000/api/settings');
          const data = await response.json();
          if (data.llm_model) {
            setLlmModel(data.llm_model);
          }
        } catch (error) {
            console.error("Failed to fetch settings:", error);
        }
      };
      fetchSettings();
    }
  }, [isOpen]);

  // モデル設定をバックエンドに送信
  const handleSaveModelSettings = async () => {
    try {
        await fetch('http://localhost:8000/api/settings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ llm_model: llmModel }),
        });
        alert('Model settings saved!');
        onClose();
    } catch (error) {
        alert('Failed to save model settings.');
    }
  };

  // Gitリポジトリをクローンするリクエストを送信
  const handleCloneRepo = async () => {
    if (!repoUrl) {
        alert('Repository URL is required.');
        return;
    }
    try {
        await fetch('http://localhost:8000/api/git/clone', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ repo_url: repoUrl }),
        });
        alert('Cloning process started. Check agent logs for details.');
        onClose();
    } catch (error) {
        alert('Failed to start cloning process.');
    }
  };


  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>Settings</DialogTitle>
          <DialogDescription>
            Configure your agent and project settings here.
          </DialogDescription>
        </DialogHeader>
        <Tabs defaultValue="model">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="model">Model</TabsTrigger>
            <TabsTrigger value="git">Git</TabsTrigger>
          </TabsList>
          <TabsContent value="model">
            <div className="grid gap-4 py-4">
              <div className="grid grid-cols-4 items-center gap-4">
                <Label htmlFor="llm-model" className="text-right">
                  LLM Model
                </Label>
                <Select value={llmModel} onValueChange={setLlmModel}>
                    <SelectTrigger className="col-span-3">
                        <SelectValue placeholder="Select a model" />
                    </SelectTrigger>
                    <SelectContent>
                        <SelectItem value="maverick">Maverick (Default)</SelectItem>
                        <SelectItem value="qwen3">Qwen3</SelectItem>
                        <SelectItem value="deepseek">DeepSeek</SelectItem>
                        <SelectItem value="qwen2.5">Qwen2.5</SelectItem>
                    </SelectContent>
                </Select>
              </div>
            </div>
            <DialogFooter>
              <Button onClick={handleSaveModelSettings}>Save changes</Button>
            </DialogFooter>
          </TabsContent>
          <TabsContent value="git">
            <div className="grid gap-4 py-4">
              <div className="grid grid-cols-4 items-center gap-4">
                <Label htmlFor="repo-url" className="text-right">
                  Repo URL
                </Label>
                <Input
                  id="repo-url"
                  value={repoUrl}
                  onChange={(e) => setRepoUrl(e.target.value)}
                  className="col-span-3"
                  placeholder="https://github.com/user/repo.git"
                />
              </div>
            </div>
            <DialogFooter>
              <Button onClick={handleCloneRepo}>Clone Repository</Button>
            </DialogFooter>
          </TabsContent>
        </Tabs>
      </DialogContent>
    </Dialog>
  );
}