"use client";

import { useEffect, useMemo, useState } from "react";
import { api, formatDate, formatMoney } from "@/lib/api";
import type { Order, Product } from "@/lib/types";
import { Badge, Button, Card, DangerButton, EmptyState, ErrorMessage, LoadingState } from "@/components/ui";

function orderTone(status: string) {
  if (status === "done") return "green" as const;
  if (status === "cancelled") return "red" as const;
  return "yellow" as const;
}

export default function OrdersPage() {
  const [orders, setOrders] = useState<Order[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function loadData() {
    const [orderData, productData] = await Promise.all([api.orders(), api.products()]);
    setOrders(orderData);
    setProducts(productData);
  }

  useEffect(() => {
    loadData()
      .catch((err) => setError(err instanceof Error ? err.message : "Buyurtmalarni yuklab bo‘lmadi"))
      .finally(() => setLoading(false));
  }, []);

  const productMap = useMemo(() => new Map(products.map((product) => [product.id, product.name])), [products]);

  async function run(orderId: number, action: () => Promise<unknown>) {
    setBusyId(orderId);
    setError(null);
    try {
      await action();
      await loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Buyurtma amali bajarilmadi");
    } finally {
      setBusyId(null);
    }
  }

  return (
    <section className="space-y-4">
      <div>
        <h1 className="text-2xl font-semibold text-slate-950">Buyurtmalar</h1>
        <p className="text-sm text-slate-500">Yangi buyurtmalarni ko‘ring, yakunlang yoki bekor qiling.</p>
      </div>
      <ErrorMessage message={error} />
      {loading ? <LoadingState /> : orders.length === 0 ? <EmptyState label="Hali buyurtma yo‘q." /> : (
        <Card className="overflow-x-auto p-0">
          <table className="w-full min-w-[1100px] text-left text-sm">
            <thead className="border-b bg-slate-50 text-slate-500">
              <tr>
                <th className="p-3">Mijoz</th>
                <th className="p-3">Mahsulot</th>
                <th className="p-3">Soni</th>
                <th className="p-3">Umumiy narx</th>
                <th className="p-3">Manzil</th>
                <th className="p-3">Izoh</th>
                <th className="p-3">Holat</th>
                <th className="p-3">Yaratilgan</th>
                <th className="p-3">Amallar</th>
              </tr>
            </thead>
            <tbody>
              {orders.map((order) => (
                <tr key={order.id} className="border-b align-top last:border-0">
                  <td className="p-3">
                    <div className="font-medium text-slate-950">{order.customer_name}</div>
                    <div className="text-slate-500">{order.phone}</div>
                  </td>
                  <td className="p-3">
                    {order.items && order.items.length > 0 ? (
                      <div className="space-y-1">
                        {order.items.map((item) => (
                          <div key={`${order.id}-${item.product_id}`} className="text-slate-700">
                            {item.product_name} x {item.quantity}
                          </div>
                        ))}
                      </div>
                    ) : (
                      productMap.get(order.product_id ?? 0) ?? `#${order.product_id ?? "-"}`
                    )}
                  </td>
                  <td className="p-3">
                    {order.items && order.items.length > 0
                      ? order.items.reduce((total, item) => total + item.quantity, 0)
                      : order.quantity ?? "-"}
                  </td>
                  <td className="p-3">{formatMoney(order.total_price)}</td>
                  <td className="max-w-xs p-3 text-slate-700">{order.address}</td>
                  <td className="max-w-xs p-3 text-slate-500">{order.comment || "-"}</td>
                  <td className="p-3"><Badge tone={orderTone(order.status)}>{order.status}</Badge></td>
                  <td className="p-3 text-slate-500">{formatDate(order.created_at)}</td>
                  <td className="p-3">
                    <div className="flex gap-2">
                      <Button disabled={busyId === order.id || order.status === "done"} onClick={() => run(order.id, () => api.markOrderDone(order.id))}>Yakunlash</Button>
                      <DangerButton disabled={busyId === order.id || order.status === "cancelled"} onClick={() => run(order.id, () => api.updateOrderStatus(order.id, "cancelled"))}>Bekor qilish</DangerButton>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}
    </section>
  );
}
