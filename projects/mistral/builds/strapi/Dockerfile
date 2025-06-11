FROM node:22-slim
# Installing libvips-dev for sharp Compatibility

# Install dependencies for native modules
RUN apt-get update && apt-get install -y \
	build-essential \
	python3 \
	git \
	libvips-dev \
	&& rm -rf /var/lib/apt/lists/*


ARG NODE_ENV=development
ENV NODE_ENV=${NODE_ENV}

WORKDIR /opt/
COPY package.json package-lock.json ./
# RUN npm install -g node-gyp
# RUN npm config set fetch-retry-maxtimeout 600000 -g && npm install
RUN npm config set fetch-retry-maxtimeout 600000 -g && npm install --build-from-source
ENV PATH=/opt/node_modules/.bin:$PATH

WORKDIR /opt/app
# COPY . .
COPY --chown=node:node . .
# RUN chown -R node:node /opt/app
RUN ["npm", "run", "build"]
RUN chown -R node:node /opt/app/.strapi
RUN chown -R node:node /opt/app/dist


COPY entrypoint.sh /opt/app/entrypoint.sh
RUN chmod +x /opt/app/entrypoint.sh
USER node
RUN mkdir -p /opt/app/public/uploads
EXPOSE 1337

ENTRYPOINT ["/opt/app/entrypoint.sh"]
