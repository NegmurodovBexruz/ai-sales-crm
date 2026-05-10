"use client";

import { useEffect, useState } from "react";
import { api, formatMoney } from "@/lib/api";
import type { OperatorProduct } from "@/lib/types";
import { Badge, Card, EmptyState, ErrorMessage, LoadingState } from "@/components/ui";

function statusTone(status: string) {
  if (status === "active") return "green" as const;
  if (status === "low_stock") return "yellow" as const;
  return "red" as const;
}

export default function OperatorProductsPage() {
  const [products, setProducts] = useState<OperatorProduct[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.operatorProducts()
      .then(setProducts)
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load products"))
      .finally(() => setLoading(false));
  }, []);

  return (
    <section className="space-y-4">
      <div>
        <h1 className="text-2xl font-semibold text-slate-950">Products</h1>
        <p className="text-sm text-slate-500">Read-only product catalog for your business.</p>
      </div>
      <ErrorMessage message={error} />
      {loading ? <LoadingState /> : products.length === 0 ? (
        <EmptyState label="No products found." />
      ) : (
        <Card className="overflow-x-auto p-0">
          <table className="w-full min-w-[900px] text-left text-sm">
            <thead className="border-b bg-slate-50 text-slate-500">
              <tr>
                <th className="p-3">Name</th>
                <th className="p-3">Category</th>
                <th className="p-3">Price</th>
                <th className="p-3">Discount</th>
                <th className="p-3">Stock</th>
                <th className="p-3">Status</th>
                <th className="p-3">Description</th>
              </tr>
            </thead>
            <tbody>
              {products.map((product) => (
                <tr key={product.id} className="border-b last:border-0 align-top">
                  <td className="p-3 font-medium text-slate-950">{product.name}</td>
                  <td className="p-3 text-slate-700">{product.category || "-"}</td>
                  <td className="p-3 text-slate-700">{formatMoney(product.price)}</td>
                  <td className="p-3 text-slate-700">{product.discount_price ? formatMoney(product.discount_price) : "-"}</td>
                  <td className="p-3 text-slate-700">{product.stock_count}</td>
                  <td className="p-3">
                    <Badge tone={statusTone(product.availability_status)}>{product.availability_status}</Badge>
                  </td>
                  <td className="max-w-md p-3 text-slate-600">{product.description || "-"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}
    </section>
  );
}
