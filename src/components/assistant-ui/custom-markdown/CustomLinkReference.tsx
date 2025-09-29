"use client"

import { ExternalLinkIcon } from "lucide-react";
import { type FC } from "react";
import { cn } from "@/lib/utils";


/**
 * Component that handles markdown format
 * [link-(....)]
 */

// Props for the link placeholder component
interface CustomLinkReferenceProps {
  url: string;
  className?: string;
}

// Placeholder component for [link-(url)] patterns
export const CustomLinkReference: FC<CustomLinkReferenceProps> = ({ 
  url, 
  className 
}) => {
  const handleClick = (e: React.MouseEvent) => {
    e.preventDefault();
    window.open(url, '_blank', 'noopener,noreferrer');
  };

  // Extract domain for display
  const getDomain = (url: string) => {
    try {
      const domain = new URL(url).hostname;
      return domain.replace('www.', '');
    } catch {
      return url.length > 30 ? url.substring(0, 30) + '...' : url;
    }
  };

  return (
    <button
      onClick={handleClick}
      className={cn(
        "aui-link-placeholder inline-flex items-center gap-1 rounded-md bg-primary/5 px-2 py-1 text-sm font-medium text-primary/80 hover:bg-primary/10 hover:text-primary transition-colors border border-primary/15 hover:border-primary/25 mx-2",
        className
      )}
      title={`Open link: ${url}`}
    >
      <ExternalLinkIcon className="h-3 w-3" />
      <span>{getDomain(url)}</span>
    </button>
  );
};