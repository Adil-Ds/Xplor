import { RouterProvider } from "react-router";
import { router } from "./routes";

export default function App() {
  return (
    <div className="dark">
      <RouterProvider router={router} />
    </div>
  );
}
