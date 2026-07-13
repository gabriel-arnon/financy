import { AcceptReimbursementInvitationContent } from "@/components/accept-reimbursement-invitation-content";

export default async function AcceptReimbursementInvitationPage({
  searchParams,
}: {
  searchParams: Promise<{ token?: string }>;
}) {
  const params = await searchParams;
  return <AcceptReimbursementInvitationContent token={params.token ?? ""} />;
}
