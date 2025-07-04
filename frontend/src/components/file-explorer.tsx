
'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { ChevronRight, Folder, File } from "lucide-react";

interface FileEntry {
  name: string;
  is_dir: boolean;
  path: string;
}

interface FileNodeProps {
  entry: FileEntry;
}

function FileNode({ entry }: FileNodeProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [children, setChildren] = useState<FileEntry[]>([]);

  const fetchChildren = async () => {
    if (entry.is_dir) {
      const response = await fetch(`http://localhost:8000/api/files?path=${entry.path}`);
      const data = await response.json();
      if (data && !data.error) {
        setChildren(data);
      }
    }
  };

  const handleToggle = () => {
    setIsOpen(!isOpen);
    if (!isOpen && entry.is_dir && children.length === 0) {
      fetchChildren();
    }
  };

  return (
    <div className="ml-4">
      {entry.is_dir ? (
        <Collapsible open={isOpen} onOpenChange={handleToggle}>
          <CollapsibleTrigger className="flex items-center space-x-1 cursor-pointer">
            <ChevronRight className={`h-4 w-4 transition-transform ${isOpen ? 'rotate-90' : ''}`} />
            <Folder className="h-4 w-4 text-yellow-500" />
            <span>{entry.name}</span>
          </CollapsibleTrigger>
          <CollapsibleContent>
            {children.map((child) => (
              <FileNode key={child.path} entry={child} />
            ))}
          </CollapsibleContent>
        </Collapsible>
      ) : (
        <div className="flex items-center space-x-1">
          <File className="h-4 w-4 text-gray-500" />
          <span>{entry.name}</span>
        </div>
      )}
    </div>
  );
}

export function FileExplorer() {
  const [rootFiles, setRootFiles] = useState<FileEntry[]>([]);

  useEffect(() => {
    const fetchRootFiles = async () => {
      const response = await fetch('http://localhost:8000/api/files');
      const data = await response.json();
      if (data && !data.error) {
        setRootFiles(data);
      }
    };
    fetchRootFiles();
  }, []);

  return (
    <Card className="h-full flex flex-col">
      <CardHeader>
        <CardTitle>File Explorer</CardTitle>
      </CardHeader>
      <CardContent className="flex-grow">
        <ScrollArea className="h-full w-full pr-4">
          {rootFiles.map((entry) => (
            <FileNode key={entry.path} entry={entry} />
          ))}
        </ScrollArea>
      </CardContent>
    </Card>
  );
}
