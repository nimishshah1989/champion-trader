FROM node:22-slim

# Pin pnpm to the version that produced pnpm-lock.yaml (lockfileVersion 9.0).
# `pnpm@latest` pulls pnpm 11, which imports node:sqlite and crashes on Node < 22.
RUN corepack enable && corepack prepare pnpm@10.33.0 --activate

WORKDIR /app

COPY package.json pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile

COPY . .

ARG NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL

RUN pnpm build

EXPOSE 3000

CMD ["pnpm", "start"]
