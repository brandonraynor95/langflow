import type React from "react";
import { forwardRef } from "react";
import KubernetesSvg from "./kubernetes.svg?react";

export const KubernetesIcon = forwardRef<
  SVGSVGElement,
  React.ComponentPropsWithoutRef<"svg">
>((props, ref) => {
  return <KubernetesSvg ref={ref} {...props} />;
});
