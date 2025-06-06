import * as ToastPrimitive from "@radix-ui/react-toast";
import { useState } from "react";

export function Toast({ message, duration = 3000 }) {
  const [open, setOpen] = useState(true);

  return (
    <ToastPrimitive.Provider swipeDirection="right">
      <ToastPrimitive.Root
        className="fixed bottom-4 right-4 bg-white border rounded-md px-4 py-2 shadow-lg"
        open={open}
        onOpenChange={setOpen}
        duration={duration}
      >
        <ToastPrimitive.Title className="text-sm font-medium">{message}</ToastPrimitive.Title>
      </ToastPrimitive.Root>
      <ToastPrimitive.Viewport />
    </ToastPrimitive.Provider>
  );
}
