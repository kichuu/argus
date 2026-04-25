import { Chip } from "@/components/ui/Chip";
import { Dot } from "@/components/ui/Dot";

type Props = {
  online: boolean;
  loading?: boolean;
  className?: string;
};

export function MockBadge({ online, loading, className }: Props) {
  if (loading) {
    return (
      <Chip tone="default" className={className}>
        <Dot tone="ink" />
        <span style={{ marginLeft: 6 }}>checking · api</span>
      </Chip>
    );
  }
  if (online) {
    return (
      <Chip tone="green" className={className}>
        <Dot tone="green" />
        <span style={{ marginLeft: 6 }}>live · api</span>
      </Chip>
    );
  }
  return (
    <Chip tone="amber" className={className}>
      <Dot tone="amber" pulse />
      <span style={{ marginLeft: 6 }}>offline · mock</span>
    </Chip>
  );
}
