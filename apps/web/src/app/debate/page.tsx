import { Suspense } from "react";
import { DebateRoom } from "@/components/screens/DebateRoom";

export default function Page() {
  return (
    <Suspense fallback={null}>
      <DebateRoom />
    </Suspense>
  );
}
