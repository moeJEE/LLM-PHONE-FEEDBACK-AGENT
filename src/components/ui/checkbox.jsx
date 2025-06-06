import * as CheckboxPrimitive from "@radix-ui/react-checkbox";
import { Check } from "lucide-react";

export function Checkbox({ checked, onCheckedChange }) {
  return (
    <CheckboxPrimitive.Root
      checked={checked}
      onCheckedChange={onCheckedChange}
      className="w-5 h-5 border border-gray-300 rounded hover:bg-gray-100 flex items-center justify-center"
    >
      <CheckboxPrimitive.Indicator>
        <Check className="w-4 h-4 text-black" />
      </CheckboxPrimitive.Indicator>
    </CheckboxPrimitive.Root>
  );
}
