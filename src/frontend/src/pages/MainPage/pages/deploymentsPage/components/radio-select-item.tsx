import ForwardedIconComponent from "@/components/common/genericIconComponent";
import { cn } from "@/utils/utils";

interface RadioSelectItemProps {
  selected: boolean;
  onChange: () => void;
  name: string;
  value: string;
  children: React.ReactNode;
  "data-testid"?: string;
  className?: string;
}

export function RadioSelectItem({
  selected,
  onChange,
  name,
  value,
  children,
  "data-testid": testId,
  className,
}: RadioSelectItemProps) {
  return (
    <label
      data-testid={testId}
      className={cn(
        "flex w-full cursor-pointer items-center gap-4 rounded-xl border bg-muted p-3 text-left transition-colors",
        selected ? "border-primary" : "border-transparent hover:border-border",
        className,
      )}
    >
      <input
        type="radio"
        name={name}
        value={value}
        checked={selected}
        onChange={onChange}
        className="sr-only"
      />
      <span
        className={cn(
          "flex h-5 w-5 flex-shrink-0 items-center justify-center rounded",
          selected
            ? "bg-primary text-primary-foreground"
            : "border border-muted-foreground bg-background",
        )}
      >
        {selected && (
          <ForwardedIconComponent name="Check" className="h-3.5 w-3.5" />
        )}
      </span>
      {children}
    </label>
  );
}
