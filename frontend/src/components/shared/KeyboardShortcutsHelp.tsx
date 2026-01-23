'use client';

import { useState, useImperativeHandle, forwardRef } from 'react';
import { Keyboard } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { getShortcutGroups } from '@/hooks/useKeyboardShortcuts';

export interface KeyboardShortcutsHelpRef {
  open: () => void;
  close: () => void;
}

export const KeyboardShortcutsHelp = forwardRef<KeyboardShortcutsHelpRef>(
  function KeyboardShortcutsHelp(_, ref) {
    const [isOpen, setIsOpen] = useState(false);
    const shortcutGroups = getShortcutGroups();

    useImperativeHandle(ref, () => ({
      open: () => setIsOpen(true),
      close: () => setIsOpen(false),
    }));

    return (
      <Dialog open={isOpen} onOpenChange={setIsOpen}>
        <DialogContent className="max-w-2xl max-h-[80vh] overflow-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Keyboard className="h-5 w-5" />
              Keyboard Shortcuts
            </DialogTitle>
            <DialogDescription>
              Use these shortcuts to navigate and trade faster.
            </DialogDescription>
          </DialogHeader>

          <div className="grid gap-6 py-4">
            {shortcutGroups.map((group) => (
              <div key={group.category}>
                <h3 className="text-sm font-semibold text-muted-foreground mb-3">
                  {group.category}
                </h3>
                <div className="space-y-2">
                  {group.shortcuts.map((shortcut) => (
                    <div
                      key={shortcut.keys}
                      className="flex items-center justify-between py-1.5 px-2 rounded hover:bg-muted/50"
                    >
                      <span className="text-sm">{shortcut.description}</span>
                      <kbd className="ml-4 inline-flex items-center gap-1 rounded border bg-muted px-2 py-1 font-mono text-xs text-muted-foreground">
                        {shortcut.keys.split(' ').map((part, i) => (
                          <span key={i}>
                            {part === 'then' ? (
                              <span className="text-muted-foreground/60">→</span>
                            ) : (
                              <span className="bg-background px-1.5 py-0.5 rounded border">
                                {part}
                              </span>
                            )}
                          </span>
                        ))}
                      </kbd>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>

          <div className="text-center text-xs text-muted-foreground pt-4 border-t">
            Press <kbd className="px-1.5 py-0.5 rounded border bg-muted">?</kbd> anytime to show this help
          </div>
        </DialogContent>
      </Dialog>
    );
  }
);

