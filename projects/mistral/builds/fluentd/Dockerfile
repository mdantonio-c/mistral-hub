FROM fluent/fluentd:v1.17-debian

# Install required packages for healthcheck and log management
USER root
RUN apt-get update && \
    apt-get install -y netcat-traditional findutils && \
    rm -rf /var/lib/apt/lists/*

# Create necessary directories
RUN mkdir -p /fluentd/log /var/log/fluentd /var/log/fluentd/buffer && \
    chown -R fluent:fluent /fluentd/log /var/log/fluentd

# Copy configuration files
COPY fluent.conf /fluentd/etc/fluent.conf
COPY log_cleanup.sh /usr/local/bin/log_cleanup.sh
COPY entrypoint-daemon.sh /usr/local/bin/entrypoint.sh
COPY manual_cleanup.sh /usr/local/bin/manual_cleanup.sh

# Set permissions
RUN chmod +x /usr/local/bin/log_cleanup.sh && \
    chmod +x /usr/local/bin/entrypoint.sh && \
    chmod +x /usr/local/bin/manual_cleanup.sh

USER fluent

# Set the custom entrypoint
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]

# Optional: install plugins if needed
# RUN fluent-gem install fluent-plugin-elasticsearch