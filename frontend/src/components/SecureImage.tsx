import { useEffect, useState } from "react";

import { API_BASE } from "../api";
import { getToken, sessionGeneration } from "../auth";

type Props = {
  src: string;
  alt: string;
  className?: string;
};

export default function SecureImage({ src, alt, className }: Props) {
  const [resolvedSrc, setResolvedSrc] = useState<string | null>(null);

  useEffect(() => {
    setResolvedSrc(null);
    if (!src.startsWith("private://")) {
      setResolvedSrc(src);
      return;
    }

    const controller = new AbortController();
    let objectUrl: string | null = null;
    const key = src.slice("private://".length);
    const token = getToken();
    const generation = sessionGeneration();

    fetch(API_BASE + "/assets/" + encodeURI(key), {
      headers: token ? { Authorization: "Bearer " + token } : {},
      signal: controller.signal,
      cache: "no-store",
    })
      .then((response) => {
        if (!response.ok) throw new Error("Asset load failed");
        return response.blob();
      })
      .then((blob) => {
        if (controller.signal.aborted || getToken() !== token || sessionGeneration() !== generation) return;
        objectUrl = URL.createObjectURL(blob);
        setResolvedSrc(objectUrl);
      })
      .catch(() => {
        if (!controller.signal.aborted) setResolvedSrc(null);
      });

    return () => {
      controller.abort();
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [src]);

  if (!resolvedSrc) return <div className="imagePlaceholder">Image unavailable</div>;
  return <img className={className} src={resolvedSrc} alt={alt} />;
}
