import { ProfilePanel } from "@/components/profile";

export const metadata = { title: "Profile" };

export default function ProfilePage() {
  return <><header className="page-header"><p className="eyebrow">Profile</p><h1>Your learning identity</h1><p>Manage the public information attached to your EKLAVYA progress.</p></header><ProfilePanel /></>;
}
