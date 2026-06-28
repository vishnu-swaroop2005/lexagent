'use client';

import { useRef, useEffect, useState, useCallback } from 'react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { Undo2, Trash2 } from 'lucide-react';

interface SignatureCanvasProps {
  onSignature: (base64Png: string) => void;
  width?: number;
  height?: number;
  className?: string;
}

interface Point {
  x: number;
  y: number;
}

export function SignatureCanvas({
  onSignature,
  width = 500,
  height = 200,
  className,
}: SignatureCanvasProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [isDrawing, setIsDrawing] = useState(false);
  const [hasContent, setHasContent] = useState(false);
  const [history, setHistory] = useState<ImageData[]>([]);

  const getContext = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return null;
    const ctx = canvas.getContext('2d');
    if (!ctx) return null;
    return ctx;
  }, []);

  const getCoords = useCallback(
    (e: React.MouseEvent | React.TouchEvent | MouseEvent | TouchEvent): Point | null => {
      const canvas = canvasRef.current;
      if (!canvas) return null;
      const rect = canvas.getBoundingClientRect();
      const scaleX = canvas.width / rect.width;
      const scaleY = canvas.height / rect.height;

      if ('touches' in e) {
        const touch = e.touches[0];
        if (!touch) return null;
        return {
          x: (touch.clientX - rect.left) * scaleX,
          y: (touch.clientY - rect.top) * scaleY,
        };
      }
      return {
        x: ((e as MouseEvent).clientX - rect.left) * scaleX,
        y: ((e as MouseEvent).clientY - rect.top) * scaleY,
      };
    },
    []
  );

  const saveState = useCallback(() => {
    const ctx = getContext();
    const canvas = canvasRef.current;
    if (!ctx || !canvas) return;
    const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
    setHistory((prev) => [...prev.slice(-20), imageData]);
  }, [getContext]);

  const startDrawing = useCallback(
    (e: React.MouseEvent | React.TouchEvent) => {
      e.preventDefault();
      const coords = getCoords(e);
      if (!coords) return;
      const ctx = getContext();
      if (!ctx) return;

      saveState();
      ctx.beginPath();
      ctx.moveTo(coords.x, coords.y);
      setIsDrawing(true);
    },
    [getCoords, getContext, saveState]
  );

  const draw = useCallback(
    (e: React.MouseEvent | React.TouchEvent) => {
      e.preventDefault();
      if (!isDrawing) return;
      const coords = getCoords(e);
      if (!coords) return;
      const ctx = getContext();
      if (!ctx) return;

      ctx.lineWidth = 2.5;
      ctx.lineCap = 'round';
      ctx.lineJoin = 'round';
      ctx.strokeStyle = '#1a1a1a';
      ctx.lineTo(coords.x, coords.y);
      ctx.stroke();
      setHasContent(true);
    },
    [isDrawing, getCoords, getContext]
  );

  const stopDrawing = useCallback(() => {
    if (!isDrawing) return;
    const ctx = getContext();
    if (ctx) ctx.closePath();
    setIsDrawing(false);

    if (hasContent) {
      const canvas = canvasRef.current;
      if (canvas) {
        onSignature(canvas.toDataURL('image/png'));
      }
    }
  }, [isDrawing, getContext, hasContent, onSignature]);

  const clearCanvas = useCallback(() => {
    const ctx = getContext();
    const canvas = canvasRef.current;
    if (!ctx || !canvas) return;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    setHasContent(false);
    setHistory([]);
    onSignature('');
  }, [getContext, onSignature]);

  const undo = useCallback(() => {
    if (history.length === 0) return;
    const ctx = getContext();
    const canvas = canvasRef.current;
    if (!ctx || !canvas) return;

    const previous = history[history.length - 1];
    ctx.putImageData(previous, 0, 0);
    setHistory((prev) => prev.slice(0, -1));

    const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
    const isEmpty = !imageData.data.some((channel, i) => i % 4 === 3 && channel !== 0);
    setHasContent(!isEmpty);

    if (!isEmpty) {
      onSignature(canvas.toDataURL('image/png'));
    } else {
      onSignature('');
    }
  }, [history, getContext, onSignature]);

  // Prevent scroll on touch devices when drawing on canvas
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const preventScroll = (e: TouchEvent) => {
      if (isDrawing) {
        e.preventDefault();
      }
    };

    canvas.addEventListener('touchmove', preventScroll, { passive: false });
    return () => {
      canvas.removeEventListener('touchmove', preventScroll);
    };
  }, [isDrawing]);

  return (
    <div className={cn('space-y-3', className)}>
      <div className="border-2 border-dashed border-gray-300 rounded-lg bg-white overflow-hidden">
        <canvas
          ref={canvasRef}
          width={width}
          height={height}
          className="w-full cursor-crosshair touch-none"
          style={{ height: `${height}px` }}
          onMouseDown={startDrawing}
          onMouseMove={draw}
          onMouseUp={stopDrawing}
          onMouseLeave={stopDrawing}
          onTouchStart={startDrawing}
          onTouchMove={draw}
          onTouchEnd={stopDrawing}
        />
        {!hasContent && (
          <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
            <p className="text-gray-400 text-sm">Draw your signature here</p>
          </div>
        )}
      </div>
      <div className="flex gap-2">
        <Button type="button" variant="outline" size="sm" onClick={undo} disabled={history.length === 0}>
          <Undo2 className="mr-1 h-3 w-3" />
          Undo
        </Button>
        <Button type="button" variant="outline" size="sm" onClick={clearCanvas} disabled={!hasContent}>
          <Trash2 className="mr-1 h-3 w-3" />
          Clear
        </Button>
      </div>
    </div>
  );
}
