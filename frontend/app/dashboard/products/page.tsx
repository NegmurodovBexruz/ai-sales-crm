"use client";

import { FormEvent, useEffect, useState } from "react";
import { api, formatMoney } from "@/lib/api";
import type { Business, Product } from "@/lib/types";
import { Badge, Button, Card, DangerButton, EmptyState, ErrorMessage, Input, Label, LoadingState, SecondaryButton, Textarea } from "@/components/ui";

type ProductForm = {
  name: string;
  description: string;
  category: string;
  price: string;
  discount_price: string;
  stock_count: string;
  image_url: string;
  tags: string;
};

const emptyForm: ProductForm = {
  name: "",
  description: "",
  category: "",
  price: "",
  discount_price: "",
  stock_count: "0",
  image_url: "",
  tags: ""
};

function statusFor(stock: number) {
  if (stock === 0) return { label: "Qolmadi", tone: "red" as const };
  if (stock <= 10) return { label: "Kam qoldi", tone: "yellow" as const };
  return { label: "Mavjud", tone: "green" as const };
}

export default function ProductsPage() {
  const [business, setBusiness] = useState<Business | null>(null);
  const [products, setProducts] = useState<Product[]>([]);
  const [form, setForm] = useState<ProductForm>(emptyForm);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function loadData() {
    const [businessMe, productData] = await Promise.all([api.businessMe(), api.products()]);
    setBusiness(businessMe.business);
    setProducts(productData);
  }

  useEffect(() => {
    loadData()
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load products"))
      .finally(() => setLoading(false));
  }, []);

  function startEdit(product: Product) {
    setEditingId(product.id);
    setForm({
      name: product.name,
      description: product.description ?? "",
      category: product.category ?? "",
      price: String(product.price),
      discount_price: product.discount_price ? String(product.discount_price) : "",
      stock_count: String(product.stock_count),
      image_url: product.image_url ?? "",
      tags: product.tags ?? ""
    });
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (!business) {
      setError("Create a business first before adding products.");
      return;
    }
    setSaving(true);
    setError(null);
    const payload = {
      business_id: business.id,
      name: form.name,
      description: form.description || null,
      category: form.category || null,
      price: Number(form.price),
      discount_price: form.discount_price ? Number(form.discount_price) : null,
      stock_count: Number(form.stock_count || 0),
      image_url: form.image_url || null,
      tags: form.tags || null
    };
    try {
      if (editingId) {
        await api.updateProduct(editingId, payload);
      } else {
        await api.createProduct(payload);
      }
      setForm(emptyForm);
      setEditingId(null);
      await loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save product");
    } finally {
      setSaving(false);
    }
  }

  async function mutate(action: () => Promise<unknown>) {
    setError(null);
    try {
      await action();
      await loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Action failed");
    }
  }

  return (
    <section className="space-y-4">
      <div>
        <h1 className="text-2xl font-semibold text-slate-950">Products</h1>
        <p className="text-sm text-slate-500">Manage catalog items and stock counts.</p>
      </div>
      <ErrorMessage message={error} />
      <Card>
        <form onSubmit={onSubmit} className="grid gap-4 lg:grid-cols-4">
          <div>
            <Label>Name</Label>
            <Input value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} required />
          </div>
          <div>
            <Label>Category</Label>
            <Input value={form.category} onChange={(event) => setForm({ ...form, category: event.target.value })} />
          </div>
          <div>
            <Label>Price</Label>
            <Input type="number" min="0" step="0.01" value={form.price} onChange={(event) => setForm({ ...form, price: event.target.value })} required />
          </div>
          <div>
            <Label>Discount price</Label>
            <Input type="number" min="0" step="0.01" value={form.discount_price} onChange={(event) => setForm({ ...form, discount_price: event.target.value })} />
          </div>
          <div>
            <Label>Stock count</Label>
            <Input type="number" min="0" value={form.stock_count} onChange={(event) => setForm({ ...form, stock_count: event.target.value })} />
          </div>
          <div>
            <Label>Image URL</Label>
            <Input value={form.image_url} onChange={(event) => setForm({ ...form, image_url: event.target.value })} />
          </div>
          <div>
            <Label>Tags</Label>
            <Input value={form.tags} onChange={(event) => setForm({ ...form, tags: event.target.value })} placeholder="comma separated" />
          </div>
          <div className="lg:col-span-4">
            <Label>Description</Label>
            <Textarea value={form.description} onChange={(event) => setForm({ ...form, description: event.target.value })} />
          </div>
          <div className="flex gap-2 lg:col-span-4">
            <Button disabled={saving}>{saving ? "Saving..." : editingId ? "Save changes" : "Add product"}</Button>
            {editingId && <SecondaryButton type="button" onClick={() => { setEditingId(null); setForm(emptyForm); }}>Cancel edit</SecondaryButton>}
          </div>
        </form>
      </Card>
      {loading ? <LoadingState /> : products.length === 0 ? <EmptyState label="No products yet." /> : (
        <Card className="overflow-x-auto p-0">
          <table className="w-full min-w-[900px] text-left text-sm">
            <thead className="border-b bg-slate-50 text-slate-500">
              <tr>
                <th className="p-3">Product</th>
                <th className="p-3">Category</th>
                <th className="p-3">Price</th>
                <th className="p-3">Stock</th>
                <th className="p-3">Status</th>
                <th className="p-3">Actions</th>
              </tr>
            </thead>
            <tbody>
              {products.map((product) => {
                const status = statusFor(product.stock_count);
                return (
                  <tr key={product.id} className="border-b last:border-0">
                    <td className="p-3">
                      <div className="font-medium text-slate-950">{product.name}</div>
                      <div className="max-w-md truncate text-slate-500">{product.description || product.tags || "-"}</div>
                    </td>
                    <td className="p-3 text-slate-700">{product.category || "-"}</td>
                    <td className="p-3">
                      {product.discount_price ? (
                        <div><span className="mr-2 text-slate-400 line-through">{formatMoney(product.price)}</span><span className="font-medium">{formatMoney(product.discount_price)}</span></div>
                      ) : formatMoney(product.price)}
                    </td>
                    <td className="p-3">{product.stock_count}</td>
                    <td className="p-3"><Badge tone={status.tone}>{status.label}</Badge></td>
                    <td className="p-3">
                      <div className="flex flex-wrap gap-2">
                        <SecondaryButton onClick={() => mutate(() => api.increaseStock(product.id))}>+ Stock</SecondaryButton>
                        <SecondaryButton onClick={() => mutate(() => api.decreaseStock(product.id))}>- Stock</SecondaryButton>
                        <SecondaryButton onClick={() => startEdit(product)}>Edit</SecondaryButton>
                        <DangerButton onClick={() => mutate(() => api.deleteProduct(product.id))}>Delete</DangerButton>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </Card>
      )}
    </section>
  );
}
