import asyncio
import json
from decimal import Decimal
from json import JSONDecodeError
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.ai_log import AILog
from app.models.business import Business
from app.models.conversation import Conversation
from app.models.customer import Customer
from app.models.product import Product


VALID_INTENTS = {
    "product_question",
    "price_question",
    "availability_question",
    "delivery_question",
    "return_policy_question",
    "order_intent",
    "complaint",
    "operator_request",
    "irrelevant",
    "unknown",
}

FALLBACK_MESSAGES = {
    "uz_latin": "Hozir bu savolga aniq javob bera olmadim. Operator sizga yordam beradi.",
    "uz_cyrillic": "Ҳозир бу саволга аниқ жавоб бера олмадим. Оператор сизга ёрдам беради.",
    "ru": "Сейчас я не смог точно ответить на этот вопрос. Оператор вам поможет.",
}


class AIServiceNotFoundError(Exception):
    pass


class AIService:
    async def generate_customer_reply(
        self,
        db: Session,
        business_id: int,
        customer_id: int,
        customer_message: str,
    ) -> dict[str, Any]:
        business = db.scalar(select(Business).where(Business.id == business_id))
        if business is None:
            raise AIServiceNotFoundError("Business not found")

        customer = db.scalar(
            select(Customer).where(Customer.id == customer_id, Customer.business_id == business_id)
        )
        if customer is None:
            raise AIServiceNotFoundError("Customer not found")

        error_message: str | None = None
        try:
            prompt = self._build_prompt(
                business=business,
                customer=customer,
                products_context=self._load_products_context(db, business_id),
                conversation_history=self._load_conversation_history(db, customer_id),
                customer_message=customer_message,
            )
            raw_response = await self._generate_text(prompt)
            ai_response = self._parse_ai_response(raw_response, customer.language)
        except Exception as exc:
            error_message = str(exc)
            ai_response = self._fallback_response(customer.language)

        self._save_ai_log(
            db=db,
            business_id=business_id,
            customer_id=customer_id,
            user_message=customer_message,
            ai_response=ai_response,
            error_message=error_message,
        )
        return ai_response

    def _load_products_context(self, db: Session, business_id: int) -> list[dict[str, Any]]:
        products = db.scalars(select(Product).where(Product.business_id == business_id)).all()
        return [
            {
                "id": product.id,
                "name": product.name,
                "description": product.description,
                "category": product.category,
                "price": str(product.price),
                "discount_price": str(product.discount_price) if product.discount_price is not None else None,
                "stock_count": product.stock_count,
                "availability_status": product.availability_status,
            }
            for product in products
        ]

    def _load_conversation_history(self, db: Session, customer_id: int) -> list[dict[str, str | None]]:
        messages = list(
            db.scalars(
                select(Conversation)
                .where(Conversation.customer_id == customer_id)
                .order_by(Conversation.created_at.desc())
                .limit(10)
            ).all()
        )
        messages.reverse()
        return [
            {
                "sender_type": message.sender_type,
                "message_text": message.message_text,
                "intent": message.intent,
            }
            for message in messages
        ]

    def _build_prompt(
        self,
        business: Business,
        customer: Customer,
        products_context: list[dict[str, Any]],
        conversation_history: list[dict[str, str | None]],
        customer_message: str,
    ) -> str:
        language_map = {
            "uz_latin": "Uzbek Latin",
            "uz_cyrillic": "Uzbek Cyrillic",
            "ru": "Russian",
        }
        context = {
            "business": {
                "name": business.name,
                "description": business.description,
                "business_knowledge_text": business.business_knowledge_text,
                "delivery_policy": business.delivery_policy,
                "return_policy": business.return_policy,
                "working_hours": business.working_hours,
            },
            "customer": {
                "language": customer.language,
                "reply_language": language_map.get(customer.language, "Uzbek Latin"),
            },
            "products": products_context,
            "conversation_history": conversation_history,
            "customer_message": customer_message,
        }
        return (
            "You are an AI sales assistant. Return only valid JSON and no markdown.\n"
            "Rules:\n"
            "- Answer only using the product catalog and business_knowledge_text/policies below.\n"
            "- Do not invent prices, stock, delivery rules, return rules, or product data.\n"
            "- Reply in the customer's selected language.\n"
            "- If stock_count is 0, do not say the product is available.\n"
            "- If stock_count is 1-10, mention low stock when relevant.\n"
            "- If discount_price exists, mention the discount price.\n"
            "- If discount_price does not exist, do not mention any discount.\n"
            "- If the customer asks outside available knowledge, set needs_operator=true.\n"
            "- If confidence is low, set needs_operator=true.\n"
            "- Keep reply short and useful.\n"
            "- Encourage ordering only if the product is available.\n"
            "- If the customer seems close to buying, is interested in a product, asks price, "
            "availability or delivery, or says they want to order, include a short line in the "
            "reply telling them to press the order button below. Use exactly the customer's "
            "language: uz_latin: Agar buyurtma qilmoqchi bo‘lsangiz, pastdagi “Buyurtma berish” "
            "tugmasini bosing. uz_cyrillic: Агар буюртма қилмоқчи бўлсангиз, пастдаги "
            "“Буюртма бериш” тугмасини босинг. ru: Если хотите оформить заказ, нажмите кнопку "
            "«Заказать» ниже.\n"
            "- Do not say an order has already been created.\n"
            "- Do not ask for quantity, name, phone, or address.\n"
            "Allowed intent values: product_question, price_question, availability_question, "
            "delivery_question, return_policy_question, order_intent, complaint, operator_request, "
            "irrelevant, unknown.\n"
            "Required JSON shape:\n"
            '{"reply":"...","intent":"unknown","lead_score":0,"recommended_product_ids":[],'
            '"needs_operator":false,"order_intent":false,"confidence":0.0}\n'
            f"Context:\n{json.dumps(context, ensure_ascii=False, indent=2)}"
        )

    async def _generate_text(self, prompt: str) -> str:
        provider = settings.AI_PROVIDER.lower().strip()
        if provider == "gemini":
            return await self._generate_gemini_text(prompt)
        if provider == "openai":
            return await self._generate_openai_text(prompt)
        raise ValueError(f"Unsupported AI_PROVIDER: {settings.AI_PROVIDER}")

    async def _generate_openai_text(self, prompt: str) -> str:
        if not settings.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is not configured")
        try:
            from openai import AsyncOpenAI
        except ImportError as exc:
            raise ValueError("openai package is not installed") from exc

        client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        response = await client.chat.completions.create(
            model=settings.OPENAI_MODEL or "gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.2,
        )
        content = response.choices[0].message.content
        if not content:
            raise ValueError("OpenAI returned an empty response")
        return content

    async def _generate_gemini_text(self, prompt: str) -> str:
        if not settings.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY is not configured")
        try:
            import google.generativeai as genai
        except ImportError as exc:
            raise ValueError("google-generativeai package is not installed") from exc

        def generate() -> str:
            genai.configure(api_key=settings.GEMINI_API_KEY)
            model = genai.GenerativeModel(settings.GEMINI_MODEL or "gemini-1.5-flash")
            response = model.generate_content(prompt)
            if not response.text:
                raise ValueError("Gemini returned an empty response")
            return response.text

        return await asyncio.to_thread(generate)

    def _parse_ai_response(self, raw_response: str, language: str) -> dict[str, Any]:
        try:
            parsed = self._extract_json(raw_response)
        except ValueError as exc:
            raise ValueError(f"Could not parse AI JSON response: {exc}") from exc
        return self._normalize_response(parsed, language)

    def _extract_json(self, text: str) -> dict[str, Any]:
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`").strip()
            if cleaned.lower().startswith("json"):
                cleaned = cleaned[4:].strip()

        decoder = json.JSONDecoder()
        for index, char in enumerate(cleaned):
            if char != "{":
                continue
            try:
                parsed, _ = decoder.raw_decode(cleaned[index:])
            except JSONDecodeError:
                continue
            if isinstance(parsed, dict):
                return parsed
        raise ValueError("No JSON object found")

    def _normalize_response(self, data: dict[str, Any], language: str) -> dict[str, Any]:
        fallback = self._fallback_response(language)
        reply = data.get("reply")
        if not isinstance(reply, str) or not reply.strip():
            reply = fallback["reply"]

        intent = data.get("intent")
        if intent not in VALID_INTENTS:
            intent = "unknown"

        return {
            "reply": reply.strip(),
            "intent": intent,
            "lead_score": self._clamp_int(data.get("lead_score"), 0, 100),
            "recommended_product_ids": self._normalize_product_ids(data.get("recommended_product_ids")),
            "needs_operator": bool(data.get("needs_operator", intent == "unknown")),
            "order_intent": bool(data.get("order_intent", intent == "order_intent")),
            "confidence": self._clamp_float(data.get("confidence"), 0.0, 1.0),
        }

    def _fallback_response(self, language: str) -> dict[str, Any]:
        return {
            "reply": FALLBACK_MESSAGES.get(language, FALLBACK_MESSAGES["uz_latin"]),
            "intent": "unknown",
            "lead_score": 0,
            "recommended_product_ids": [],
            "needs_operator": True,
            "order_intent": False,
            "confidence": 0.0,
        }

    def _save_ai_log(
        self,
        db: Session,
        business_id: int,
        customer_id: int,
        user_message: str,
        ai_response: dict[str, Any],
        error_message: str | None,
    ) -> None:
        log = AILog(
            business_id=business_id,
            customer_id=customer_id,
            user_message=user_message,
            ai_response=ai_response["reply"],
            detected_intent=ai_response["intent"],
            confidence=Decimal(str(ai_response["confidence"])),
            error_message=error_message,
        )
        db.add(log)
        db.commit()

    def _normalize_product_ids(self, value: Any) -> list[int]:
        if not isinstance(value, list):
            return []
        product_ids: list[int] = []
        for item in value:
            try:
                product_ids.append(int(item))
            except (TypeError, ValueError):
                continue
        return product_ids

    def _clamp_int(self, value: Any, minimum: int, maximum: int) -> int:
        try:
            number = int(value)
        except (TypeError, ValueError):
            number = minimum
        return max(minimum, min(number, maximum))

    def _clamp_float(self, value: Any, minimum: float, maximum: float) -> float:
        try:
            number = float(value)
        except (TypeError, ValueError):
            number = minimum
        return max(minimum, min(number, maximum))


ai_service = AIService()
